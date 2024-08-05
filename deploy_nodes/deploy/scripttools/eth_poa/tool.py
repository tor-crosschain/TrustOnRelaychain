import json
import os
import time
import shutil
import traceback
import setting
import re
from web3 import Web3, HTTPProvider
from tools.helper.exception_helper import require
from tools.sdk.ethsdk import EthSdk
from tools.helper.utils_helper import (
    get_remote_client, 
    calc_hash, 
    exec_command_local,
    create_account_on_bu, 
    create_account_on_eth, 
    generate_account,
    generate_account_bu,
    generate_genesis_hit,
    generate_genesis_pow,
    generate_genesis_poa
)

GETH_BIN = "./blockchain/bin/geth_1.10.0"
CHAIN_TYPE = setting.CHAINTYPE_POA

class Tool(object):
    def __init__(self, print_func=None) -> None:
        self.print_func =  print if not print_func else print_func
        pass

    def pre_start(self, chain_config: dict):
        """
        start bootnode
        """
        bootnode_config = chain_config['bootnode']
        host, port, username, password = (
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
                chain_type=chain_config['chain_type'],
                bootnode_idx=bootnode_idx, 
                bootnode_config=json.dumps(bootnode_config)
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
        generate_genesis_poa(
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
            self.create_account_from_bin(GETH_BIN, password=password) # (address, key_file)
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
        genesis_account, genesis_account_file = self.create_account_from_bin(GETH_BIN, password)
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
        result = {}
        for idx, server in enumerate(server_nodes):
            key_files = [signer_files[idx]]
            host = server['host']
            port = server['port']
            username = server['username']
            password = server['password']
            
            print("deal with host: {}......".format("{}:{}".format(host, port)))
            client = get_remote_client(host, port, username, password)
            # set remote pwd
            pwd = '/root/workspace/blockchain'
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
            node_tag = node_tag[:10] + "-nodeidx-{}".format(idx)
            command="cd {pwd} && {start}".format(
                    pwd=pwd,
                    start="/root/miniconda3/bin/python scripts/start_chain.py '{chain_type}' '{chain_tag}' '{chain_config}'".format(
                        chain_type=CHAIN_TYPE,
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
                result[host] = rpcport
                chain_config['server_nodes'][idx].update({"rpcport": rpcport})
        self.print_func("checking start status...")
        for host, port in result.items():
            url = "http://{}:{}".format(host, port)
            errcnt = 0
            while True:
                try:
                    w = Web3(HTTPProvider(url, {'timeout': 60}))
                    require(w.is_connected(),"")
                    break
                except Exception:
                    self.print_func("check node({}) status, {}".format(url, errcnt))
                    time.sleep(2)
                    errcnt += 1
                    if errcnt == 15:
                        raise Exception("chain 未启动")
        return chain_config

    def start_mining(self, chain_config: dict):
        self.print_func("start mining...")
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
        self.print_func("mining finished!")
        return chain_config
    
    def generate_account_from_bin(self, geth, datadir, password='', **kwargs):
        pwdfile = os.path.join(datadir, 'pwd'+str(int(time.time()*1000)))
        os.system("echo -n '{password}' > {pwdfile}".format(password=password, pwdfile=pwdfile))
        try:
            cmd = "{geth} account new --password {pwdfile} --datadir {datadir}".format(geth=geth, pwdfile=pwdfile, datadir=datadir)
            out = exec_command_local(cmd, 'generate account')
            addrs = re.findall('Public address of the key:\s+0x([a-zA-Z0-9]*)',out)
            require(len(addrs) == 1, "generate account error, out: {}, cmd: {}".format(out, cmd))
        except Exception as e:
            raise Exception(traceback.format_exc())
        finally:
            os.remove(pwdfile)
        addr = addrs[0]
        if len(addr) % 2 == 1: addr = '0'+addr
        return '0x'+addr

    def create_account_from_bin(self, geth_path=GETH_BIN, password="", **kwargs):
        """generate account from bin获取到账户地址之后，该函数获取账户私钥文件

        Args:
            geth_path (geth bin path): geth的二进制路径
            password (str, optional): 账户密码. Defaults to "".

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        temp_data_dir = './temp_datadir_'+str(time.time()*1000)[-5:]
        if os.path.exists(temp_data_dir): 
            shutil.rmtree(temp_data_dir)
        os.makedirs(temp_data_dir)
        try:
            address = self.generate_account_from_bin(geth=geth_path,datadir=temp_data_dir, password=password)
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
        
        return address, account_file
