import json
import os
import time
import shutil
import traceback
import setting
from tools.sdk.ethsdk import EthSdk
from tools.helper.utils_helper import (
    get_remote_client, 
    calc_hash, 
    create_account_on_bu, 
    create_account_on_eth, 
    generate_account,
    generate_account_bu,
    generate_genesis_hit,
    generate_genesis_pow
)

GETH_BIN = os.path.join('bin', 'geth_hit')

class Tool(object):
    def __init__(self) -> None:
        pass

    def generate_genesis(self,) -> None:
        pass

    def pre_start(self, chain_config: dict):
        """
        start bootnode
        """
        bootnode_config = chain_config['bootnode']
        host, port, username, password, remote_dir = (
            bootnode_config['host'], 
            bootnode_config['port'], 
            bootnode_config['username'], 
            bootnode_config['password']
        )
        bootnode_idx = calc_hash(
            host, port, username, password,
            bootnode_config['bootnode_key'],
            chain_config['chain_name'], chain_config['chain_type']
        )
        client = get_remote_client(
            host, port, username, password
        )
        bootnode_config = {
            'bootnode_key': bootnode_config['bootnode_key']
        }
        stdin, stdout, stderr = client.exec_command(
            command="cd /root/workspace/blockchain && /root/miniconda3/bin/python scripts/start_chain_pre.py {chain_type} {bootnode_idx} '{bootnode_config}'".format(
                remote_dir=remote_dir, 
                chain_type=chain_config['chain_type'],
                bootnode_idx=bootnode_idx, 
                bootnode_config=json.dumps(chain_config)
            ),
        )
        out = stdout.read().decode().strip(" \n\r")
        err = stderr.read().decode().strip(" \n\r")
        if err:
            raise Exception("start bootnode failed! error: {}".format(err))
        chain_config['bootnode'].update({
            "idx":bootnode_idx,
            "enode_info": out
        })
        chain_config.update()
        return chain_config

    def create_account(self, geth_path, password=""):
        temp_data_dir = './temp_datadir_'+str(time.time()*1000)[-5:]
        if os.path.exists(temp_data_dir): 
            shutil.rmtree(temp_data_dir)
        os.makedirs(temp_data_dir)
        try:
            account = generate_account(geth=geth_path,datadir=temp_data_dir, password=password)
            keystore_path = os.path.join(temp_data_dir, 'keystore')
            account_file_name = os.listdir(keystore_path)[0]
            account_file = os.path.join(keystore_path, account_file_name)
            with open(account_file, 'r') as f:
                account_file_content = f.read()
            account_file = (account_file_name, account_file_content)
        except Exception as e:
            raise Exception(traceback.format_exc())
        finally:
            shutil.rmtree(temp_data_dir)
        return account, account_file

    def generate_genesis(self, genesis_account, signer_account_infos):
        print("生成创世区块配置......")
        gs_path = "genesis.json"+str(time.time()*1000)[-5:]
        generate_genesis_hit(
            gs_path,
            genesis_account=genesis_account, 
            signer_account=signer_account_infos,
            period=5,
            gasLimit='0x'+'f'*16
        )
        gs_conf = json.load(open(gs_path, 'r'))
        os.remove(gs_path)
        print("创世区块配置已生成")
        return gs_conf

    def start_chain(self, chain_config: dict):
        print("ready to start chain......")

        """
        为每个node创建一个signer_account，提前放入到genesis文件中；
        如果是启动链之后再创建signer_account，那么signer_account没有余额；
        提前写入到genesis中，可以直接设置余额
        """
        password = ""
        signer_account_infos = [
            self.create_account(GETH_BIN, password=password) # (address, key_file)
            for _ in range(len(chain_config['server_nodes']))
        ]
        for idx, signer in enumerate(signer_account_infos):
            chain_config['server_nodes'][idx].update(
                {'signer_account': {'address': signer[0], 'password': password}}
            )
        """
        创建genesis_account
        """
        password = ""
        genesis_account, genesis_account_file = self.create_account(GETH_BIN, password)
        chain_config.update({'genesis_account': {'address': genesis_account, 'password': password}})
        """
        使用 genesis_account 以及 signer_account 创建 genesis config
        """
        genesis_config = self.generate_genesis(
                genesis_account, 
                [signer[0] for signer in signer_account_infos] # (address, key_file) 获取 address 列表
            )
        account_files = [
            [signer[1] for signer in signer_account_infos],  # (address, key_file) 获取 keyfile 列表
            genesis_account_file
        ]
        
        server_nodes = chain_config['server_nodes']
        signer_files = account_files[0]
        genesis_file = account_files[1]
        result = {"rpcports": {}}
        for idx, server in enumerate(server_nodes):
            key_files = [signer_files[idx]]
            host = server['host']
            port = server['port']
            username = server['username']
            password = server['password']
            
            print("deal with host: {}......".format("{}:{}".format(host, port)))
            client = get_remote_client(host, port, username, password)
            # set remote pwd
            pwd = 'cd /root/workspace/blockchain'
            if idx == 0:
                key_files.append(genesis_file)
            # start chain
            # key_files = json.dumps(key_files)
            # print(key_files)
            node_config = {
                'genesis_config': genesis_config,
                'bootnode': chain_config['bootnode']['enode_info'],
                'account_files': key_files
            }
            node_tag = calc_hash(
                chain_config['chain_name'], chain_config['chain_type'], 
                host, port, username, password
            )
            node_tag += "/nodeidx-{}".format(idx)
            command="cd {pwd} && {start}".format(
                    pwd=pwd,
                    start="/root/miniconda3/bin/python scripts/start_chain.py {chain_type} {chain_tag} '{chain_config}'".format(
                        chain_type=setting.CHAINTYPE_HIT,
                        chain_tag=node_tag,
                        chain_config=json.dumps(node_config)
                    )
                )
            stdin, stdout, stderr = client.exec_command(
                command=command
            )
            
            out = stdout.read().decode()
            err = stderr.read().decode()
            if err:
                raise Exception("start chain failed! error: {}".format(err))
            if out:
                rpcport = int(out)
                chain_config['server_nodes'][idx] = rpcport
        return chain_config

    def start_mining(self, chain_config: dict):
        nodes = chain_config['server_nodes']
        for idx, node in enumerate(nodes):
            rpcport = node['rpcport']
            rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
            sdk = EthSdk(rpc,poa=True, unlock_genesis=False)
            sdk.unlockAccount(
                nodes[idx]['signer_account']['address'],
                nodes[idx]['signer_account']['password'],
                0
            )
            sdk.w3.geth.miner.stop()
            sdk.w3.geth.miner.start()
            print("节点(idx: {}, rpcport: {})挖矿已启动 !".format(idx, rpcport))