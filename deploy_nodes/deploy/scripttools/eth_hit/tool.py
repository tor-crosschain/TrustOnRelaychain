import json
import os
import time
import shutil
import traceback

from web3 import Web3,HTTPProvider
import setting
import hashlib
import re
import threading
from deploy_nodes.deploy.scripttools import tool_selector
from eth_account import account
from tools.helper import strjoin_helper
from tools.helper.exception_helper import require
from tools.sdk.ethsdk import EthSdk
from tools.helper.utils_helper import (
    auth_account,
    get_remote_client, 
    calc_hash, 
    generate_account,
    generate_genesis_hit,
)

GETH_BIN = "./blockchain/bin/geth_hit"
CHAIN_TYPE = setting.CHAINTYPE_HIT

class Tool(object):

    def __init__(self, print_func=None) -> None:
        self.print_func =  print if not print_func else print_func


    def generate_genesis(self, genesis_account, signer_account_infos):
        self.print_func("生成创世区块配置......")
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
        self.print_func("创世区块配置已生成")
        return gs_conf


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

    def start_chain(self, chain_config: dict):
        self.print_func("ready to start chain......")

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
                {'signer_account': signer}
            )
        """
        创建genesis_account
        """
        password = ""
        genesis_account = self.create_account_from_bin(GETH_BIN, password)
        chain_config.update({'genesis_account': genesis_account})
        """
        使用 genesis_account 以及 signer_account 创建 genesis config
        """
        genesis_config = self.generate_genesis(
                genesis_account['address'], 
                [signer['address'] for signer in signer_account_infos] # 获取 address 列表
            )
        account_files = [
            [(signer['key_filename'], signer["key_filecontent"]) for signer in signer_account_infos],  # 获取 keyfile 列表
            (genesis_account['key_filename'], genesis_account['key_filecontent'])
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
            
            self.print_func("deal with host: {}......".format("{}:{}".format(host, port)))
            client = get_remote_client(host, port, username, password)
            # set remote pwd
            pwd = '/root/workspace/blockchain'
            if idx == 0:
                key_files.append(genesis_file)
            # start chain
            # key_files = json.dumps(key_files)
            # self.print_func(key_files)
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
                self.print_func("node-{}: {}".format(idx, rpcport))
        self.print_func("checking start status...")
        
        for host, port in result.items():
            url = "http://{}:{}".format(host, port)
            errcnt = 0
            while True:
                try:
                    w = Web3(HTTPProvider(url, {'timeout': 60}))
                    require(w.isConnected(),"")
                    break
                except Exception:
                    self.print_func("check node({}) status, {}".format(url, errcnt))
                    time.sleep(2)
                    errcnt += 1
                    if errcnt == 15:
                        raise Exception("chain 未启动")

        self.print_func("start chain finished!")
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
            self.print_func("节点(idx: {}, rpcport: {})挖矿已启动 !".format(idx, rpcport))
        self.print_func("mining finished!")
        return chain_config

    def create_account_from_bin(self, geth_path, password=""):
        """直接从geth_bin的命令行创建账户

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
            address = generate_account(geth=geth_path,datadir=temp_data_dir, password=password)
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
        return {
                'address': address,
                'password': password,
                'key_filename': account_file[0],
                'key_filecontent': account_file[1]
            }

    def create_account_from_raw(self, password=""):
        acct = account.Account.create()
        key_filecontent = account.Account.encrypt(acct.key, password=password)
        return {
            'address': acct.address,
            'password': password,
            'private_key': acct.key.hex(),
            'key_filecontent': json.dumps(key_filecontent),
            'key_filename': str(int(time.time()))
        }
    
    def save_account_local(self, node: dict, account: dict):
        rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        ethsdk = EthSdk(rpc, poa=True)
        ethsdk.w3.geth.personal.import_raw_key(account['private_key'],account['password']) # 存储到keystore里面
    
    def create_valid_account(self, chain_config: dict, idx_node: int, password: str, **kwargs) -> dict:
        """创建有效的账户，有效是指：已授权，有余额，已解锁

        Args:
            chain_config (dict): 链配置信息
            password (str): 账户密码, 
            **kwargs: 
                - nodes: 其他节点信息，用于授权新账户

        Returns:
            chain_config: 更新后的链配置信息
        """
        nodes = chain_config['server_nodes']
        node = nodes[idx_node]
        new_account = self.create_account_from_raw(password=password)
        master_rpc = 'http://{}:{}'.format(nodes[0]['host'], nodes[0]['rpcport'])
        master_sdk = EthSdk(master_rpc,poa=True, unlock_genesis=True)
        rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        sdk = EthSdk(rpc,poa=True, unlock_genesis=False)
        sdk.w3.geth.personal.import_raw_key(new_account['private_key'],new_account['password']) # 存储到keystore里面
        flag = sdk.unlockAccount(new_account['address'], password, 0)
        auth_account(nodes, new_account=new_account['address'])
        receipt = master_sdk.sendSingleTransaction(addr_from=master_sdk.defaultAccount, addr_to=new_account['address'], value=master_sdk.toWei(1000))
        require(receipt['status'] == 1, "transfer to new address failed!")
        return new_account

    def create_default_account(self, chain_config: dict, **kwargs):
        self.print_func("creating default account...")
        nodes = chain_config['server_nodes']
        for idx, node in enumerate(nodes):
            rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
            password = hashlib.sha256(str(int(time.time()*1000)).encode('utf-8')).hexdigest()
            new_account = self.create_valid_account(chain_config, idx, password)
            chain_config['server_nodes'][idx].update({
                'default_account':new_account
            })
        return chain_config
    
    def create_gw_account(self, chain_config: dict, reset:bool=True, **kwargs):
        def gen(idx_node, node: dict, result: dict):
            password_para = hashlib.sha256(str(int(time.time()*1000)).encode('utf-8')).hexdigest()
            gw_account_on_para = self.create_valid_account(chain_config, idx_node, password_para)
            # TODO 这里是个BUG，如果这样写互联链只能用类以太坊的
            password_inter = hashlib.sha256(str(int(time.time()*1000)).encode('utf-8')).hexdigest()
            gw_account_on_inter = self.create_account_from_raw(password=password_inter)
            result[idx_node] = {
                'para': gw_account_on_para,
                'inter': gw_account_on_inter
            }

        self.print_func("creating gateway account...")
        threads = []
        result = {}
        server_nodes = chain_config['server_nodes']
        for idx_node, node in enumerate(server_nodes):
            if not node['isgw']: 
                # 节点是否要做网关
                continue 
            if not reset:
                # 是否重新创建网关
                if node.get('gw_account', None) is not None: 
                    continue
            threads.append(threading.Thread(
                target=gen,
                args=(idx_node, node, result)
            ))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for key, value in result.items():
            chain_config['server_nodes'][key].update({
                'gw_account': value
            })
        return chain_config

    def create_delegate_account(self, chain_config: dict, reset:bool=True, **kwargs):
        def gen(idx_node, gover_config:dict, result: dict):
            scripttool = tool_selector.selector(gover_config['chain_type'])
            password_gover = hashlib.sha256(str(int(time.time()*1000)).encode('utf-8')).hexdigest()
            delegate_account_gover = scripttool.create_valid_account(gover_config, 0, password_gover)
            result[idx_node] = delegate_account_gover

        self.print_func("creating delegate account...")
        gover_config = kwargs['gover_config']
        threads = []
        result = {}
        server_nodes = chain_config['server_nodes']
        for idx_node, node in enumerate(server_nodes):
            if not node['isdelegate']: 
                # 节点是否要做代表节点
                continue 
            if not reset:
                # 是否重新创建代表节点
                if node.get('delegate_account_on_gover', None) is not None: 
                    continue
            threads.append(threading.Thread(
                target=gen,
                args=(idx_node, gover_config, result)
            ))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        for key, value in result.items():
            chain_config['server_nodes'][key].update({
                'delegate_account_on_gover': value
            })
        return chain_config
    
    def get_latest_confirmed_blocks(self, chain_config: dict, last_block_number: int, threshold: int=0):
        """
        get all the latest confirmed blocks(not batch process)
        """
        rpc = 'http://{}:{}'.format(chain_config['server_nodes'][0]['host'], chain_config['server_nodes'][0]['rpcport'])
        sdk = EthSdk(rpc,poa=True)
        def _getblock(idx: int):
            """
            1. retry 3 times to prevent some network connection exception
            2. exception must be raised to stop the program if blocks cannot be got from chain
            """
            for i in range(3):
                try:
                    block = sdk.w3.eth.getBlock(idx)
                    return block
                except Exception as e:
                    self.print_func("retry {} time, msg: {}".format(i+1, str(e)))
                    time.sleep(0.5)
            raise Exception("getblock failed after 3 times retry")
        
        # main entry of get_latest_confirmed_blocks function
        self.print_func("----start to get the latest confirmed blocks")
        latest_num = sdk.w3.eth.blockNumber
        confirmed_num = latest_num - threshold # here, the '5' is not very accurate
        blocks = []
        if confirmed_num > last_block_number:
            
            while last_block_number < confirmed_num:
                last_block_number += 1
                block = _getblock(last_block_number)
                blocks.append(block)
        return blocks, last_block_number

    def reg_listen(self, chain_config: dict):

        gover_rpc = 'http://{}:{}'.format(chain_config['server_nodes'][0]['host'], chain_config['server_nodes'][0]['rpcport'])
        gover_contract_addr = chain_config['contract']['contracts']['Parachain']['address']
        gover_contract_abi = json.loads(chain_config['contract']['contracts']['Parachain']['abistr'])
        contract_info = (gover_contract_addr, gover_contract_abi)
        default_account = chain_config['server_nodes'][0]['default_account']
        account_address, account_password = default_account['address'], default_account['password']
        sdk = EthSdk(gover_rpc,poa=True)
        sdk.defaultAccount = account_address
        sdk.unlockAccount(sdk.defaultAccount, account_password, 0)

        def _check_registration(receipt, transaction):
            """
            1. get input of function[registerParallelChain]
            2. call: function[queryParallelChainIDForAccept]
            3. send tx: function[accept]
            """
            # self.print_func.info("-----check registration")
            if str(receipt['to']).lower() != str(gover_contract_addr).lower(): return
            func_input = transaction.get('input', None)
            if not func_input: return
            func, params = sdk.parse_input(contract_address=gover_contract_addr, contract_abi=gover_contract_abi, func_input=func_input)
            if not str(func).startswith('<Function registerParallelChain'): 
                # self.print_func.info("not registerParallelChain! func: {}".format(func))
                return
            self.print_func("find one registerParallelChain function, block({}), txhash({}), params[delegates]: {}".format(receipt['blockNumber'], receipt['transactionHash'].hex(), params['delegates']))
            if receipt['status'] != 1: 
                self.print_func("this reg transaction execution failed with txreceipt.status {}".format(receipt['status']))
                return
            events = sdk.parseEventFromContractMeta(
                contract_addr=gover_contract_addr,
                contract_abi=gover_contract_abi,
                tx_receipt=receipt,
                event_names=['regist']
            )
            chainid = int(events['regist'][-1]['chainID'])
            # here, chainid should be checked ">0", "=0"
            if chainid != 0:
                # 先判断是否已经审核过
                accepted = sdk.contract_call(
                    contract_address=gover_contract_addr,
                    contract_abi=gover_contract_abi,
                    exec_func='queryParallelChainAccepted',
                    func_args=[chainid]
                )
                if accepted:
                    self.print_func("已审核! chainid: {}".format(chainid))
                    return 
                # 如果没有审核，则执行 accept 方法
                errstr = 'errstr'
                tx_receipt, events = sdk.contract_transact(
                    contract_address=gover_contract_addr, 
                    contract_abi=gover_contract_abi, 
                    exec_func='accept', 
                    func_args=[chainid]
                )
                
                # 检查是否执行成功
                if tx_receipt['status'] != 1:
                    self.print_func("this accept transaction execution status != 1. please check this transaction, txhash: {}".format(tx_receipt['transactionHash'].hex()))
                else:
                    # 检查是否有错误信息
                    # 检查是否已经审核通过
                    accepted = sdk.contract_call(
                        contract_address=gover_contract_addr,
                        contract_abi=gover_contract_abi,
                        exec_func='queryParallelChainAccepted',
                        func_args=[chainid]
                    )
                    if accepted:
                        self.print_func("accept success! chainid: {}".format(chainid))
                    else:
                        self.print_func("accept failed! chainid: {}, reg_hash: {}".format(chainid, tx_receipt['transactionHash']))
            else:
                self.print_func("get chainid from chain failure, the chainid should NOT be 0. function params of queryParallelChainIDForAccept is : {}".format(chainid))

        # main entry of loop_check function
        
        self.print_func("check contract({})...".format(contract_info[0]))
        last_block_number = 0
        while True:
            blocks, last_block_number = self.get_latest_confirmed_blocks(chain_config, last_block_number)
            self.print_func('get latest {} blocks'.format(len(blocks)))
            for block in blocks:
                # logger.info("deal with block: {}".format(block['number']))
                if not (block['number'] % 100): 
                    self.print_func("block checkpoint: {}".format(block['number']))
                for idx, txhash in enumerate(block['transactions']):
                    receipt = sdk.w3.eth.getTransactionReceipt(txhash)
                    tran = sdk.w3.eth.getTransaction(txhash)
                    _check_registration(receipt,tran)
                time.sleep(0.1)
            if len(blocks) == 0:
                time.sleep(3)
            else:
                time.sleep(0.1)

    def reg(self, chain_config, delegate_account, reg_args, **kwargs):
        gover_rpc = 'http://{}:{}'.format(chain_config['server_nodes'][0]['host'], chain_config['server_nodes'][0]['rpcport'])
        gover_contract_addr = chain_config['contract']['contracts']['Parachain']['address']
        gover_contract_abi = json.loads(chain_config['contract']['contracts']['Parachain']['abistr'])
        contract_info = (gover_contract_addr, gover_contract_abi)
        sdk = EthSdk(gover_rpc,poa=True)
        receipt, events = sdk.sendrawTransaction(
            contract_address=Web3.toChecksumAddress(contract_info[0]),
            contract_abi=contract_info[1],
            exec_func='registerParallelChain',
            func_args=reg_args,
            source_args={
                'from': Web3.toChecksumAddress(delegate_account['address']),
                'hitchain': True,
                'privatekey': delegate_account['private_key']
            },
            event_names=['regist']
        )
        require(receipt['status'] == 1, "tx execution failed! txhash: {}".format(receipt['transactionHash']))
        regist_info = events['regist']
        require(len(regist_info) >= 1, "event regist is not valid. regist: {}".format(regist_info))
        chanid = regist_info[-1]['chainID']
        return int(chanid)
    
    def reg_wait_confirm(self, chain_config, reg_id, **kwargs):
        self.print_func("等待chain_id({})被确认...".format(reg_id))
        rpc = 'http://{}:{}'.format(chain_config['server_nodes'][0]['host'], chain_config['server_nodes'][0]['rpcport'])
        gover_contract_addr = chain_config['contract']['contracts']['Parachain']['address']
        gover_contract_abi = json.loads(chain_config['contract']['contracts']['Parachain']['abistr'])
        contract_info = (gover_contract_addr, gover_contract_abi)
        chainid = int(reg_id)
        sdk = EthSdk(rpc,poa=True)
        starttime = time.time()
        timeout = 30
        while True:
            state = sdk.contract_call(
                contract_address=contract_info[0],
                contract_abi=contract_info[1],
                exec_func='queryParallelChainAccepted',
                func_args=[chainid]
            )
            if state:
                self.print_func("chain_id({})已被确认...".format(reg_id))
                return
            else:
                time.sleep(5)
        

    def reg_parallel_to_gover(self, chain_config, gover_config, **kwargs):

        def get_func_args(chain):
            self.print_func("构造注册参数......")
            server_nodes = chain['server_nodes']
            associates, delegates, gws = [],[],[]
            for idx_node, node in enumerate(server_nodes):
                if node['isdelegate']: 
                    associates.append(node['default_account']['address']) 
                    delegates.append(Web3.toChecksumAddress(node['delegate_account_on_gover']['address']))
                if node['isgw']: gws.append(Web3.toChecksumAddress(node['gw_account']['inter']['address']))
            master_rpc = 'http://{}:{}'.format(server_nodes[0]['host'], server_nodes[0]['rpcport'])
            description = master_rpc
            chain_name = chain['chain_name']
            chain_type = chain['chain_type']
            asset = 'it is asset'
            func_args = [
                delegates,associates,chain_name,chain_type,asset,description,gws
            ]
            return func_args

        scripttool_gover = tool_selector.selector(gover_config['chain_type'])
        func_args = get_func_args(chain_config)
        chainid = chain_config.get('chain_id', None)
        if chainid: 
            input_char = input("平行链 {} 已经拥有 chain_id({})! 确定重新创建嘛? (y/n)".format(chain_config['chain_name'], chainid))
            # if input_char in ['y', 'yes', 'Y']:
            if input_char in ['n', 'no', 'N']:
                return
            elif input_char in ['y', 'yes', 'Y']:
                pass
            else:
                self.print_func("无效输入!")
                return
        for idx_node, node in enumerate(chain_config['server_nodes']):
            if not node['isdelegate']: continue
            self.print_func("准备注册......")
            chainid = scripttool_gover.reg(gover_config, node['delegate_account_on_gover'], func_args)
            require(chainid > 0, "chainid({}) is invalid!".format(chainid))
            break
        self.print_func("平行链 {} 注册完成! chainid: {}".format(chain_config['chain_name'], chainid))
        chain_config['chain_id'] = chainid
        return chain_config

    def deploy_gover_contract(self, chain_config, **kwargs):
        master_node = chain_config['server_nodes'][0]

        ispoa = True
        # 先把部署者账户解锁
        rpc = 'http://{host}:{port}'.format(host=master_node['host'], port=master_node['rpcport'])
        ethsdk = EthSdk(rpc, poa=ispoa)
        default_account = master_node['default_account']
        password = default_account['password']
        account = default_account['address']
        ethsdk.defaultAccount = account
        ethsdk.unlockAccount(ethsdk.defaultAccount, password, 0)

        # 多线程部署合约
        result = goverctr_manager.deploy_all(
            rpc=rpc, 
            ispoa=ispoa, 
            account=account, 
            solc_path='./blockchain/bin/solc_hit', 
            ctr_base_path='./cc_contracts/goverchain', 
            args={}
        )
        for k, v in result.items():
            print(k, v['address'])
        # 多线程绑定合约
        goverctr_manager.bind_all(rpc=rpc,ispoa=ispoa,account=account,deploy_info=result)
        chain_config['contract']['contracts'].update(result)
        return chain_config

    def deploy_parallel_contract(self, chain_config):
        master_node = chain_config['server_nodes'][0]

        # 先把部署者账户解锁
        ispoa = True
        rpc = 'http://{host}:{port}'.format(host=master_node['host'], port=master_node['rpcport'])
        ethsdk = EthSdk(rpc, poa=ispoa)
        default_account = master_node['default_account']
        password = default_account['password']
        account = default_account['address']
        ethsdk.defaultAccount = account
        ethsdk.unlockAccount(ethsdk.defaultAccount, password, 0)

        # 多线程部署合约
        result = crossctr_manager.deploy_all(
            rpc=rpc, 
            ispoa=ispoa, 
            account=account, 
            solc_path='./blockchain/bin/solc_hit', 
            ctr_base_path='cc_contracts/crosschain/solidity/v0.4.25', 
            args={'CrossSteward': (chain_config['chain_id'],)}
        )
        for k, v in result.items():
            print(k, v["address"])
        # 多线程绑定合约
        crossctr_manager.bind_all(rpc=rpc,ispoa=ispoa,account=account,deploy_info=result)
        # json.dump(result, open("crossctrmanager_result.json", 'w'))
        chain_config['contract_cross'].update(result)
        return chain_config

    def update_crossctr(self, chain_config: dict, ctr_info: tuple):
        gover_node = chain_config['server_nodes'][0]
        gover_rpc = 'http://{}:{}'.format(gover_node['host'], gover_node['rpcport'])
        gover_base = chain_config['contract']['contracts']['Parachain']
        gover_sdk = EthSdk(gover_rpc, poa=True)
        self.print_func("------ 正在治理链上更新跨链基础服务合约......")
        receipt, _ = gover_sdk.contract_transact(
            contract_address=gover_base['address'],
            contract_abi=json.loads(gover_base['abistr']),
            exec_func='updateCross',
            func_args=ctr_info
        )
        require(receipt["status"] == 1, "updateZoneCross failed!")
        self.print_func("在治理链上更新跨链合约地址 {}".format("成功" if receipt['status'] == 1 else "失败"))

    def update_crossctr_on_gover(self, chain_config, gover_config, **kwargs):
        cross_info = strjoin_helper.join(
            [
                chain_config['contract_cross']['ManagerGateway']["address"],
                chain_config['contract_cross']['ManagerGateway']["abistr"]
            ]
        )
        gover_scripttool = tool_selector.selector(chain_type=gover_config['chain_type'])
        gover_scripttool.update_crossctr(gover_config, ctr_info=(int(chain_config['chain_id']), cross_info))
        return chain_config

    def get_crossctr_info(self, chain_config: dict):
        address = chain_config['contract_cross']['ManagerGateway']['address']
        abistr = chain_config['contract_cross']['ManagerGateway']['abistr']
        crossinfo = strjoin_helper.join(
                    [address,
                    abistr]
                )
        return crossinfo

    def generate_interchain_config(self, inter_config: dict, inter_info: list):
        useful_servers = inter_config['useful_servers']
        return {
                'chain_id': inter_info[0],
                'chain_name': inter_info[1],
                'chain_type': inter_info[2],
                'bootnode': {
                    'host': useful_servers[0]['host'],
                    'port': useful_servers[0]['port'],
                    'username': useful_servers[0]['username'],
                    'password': useful_servers[0]['password'],
                    'bootnode_key': hashlib.sha256(str(inter_info[0]).encode('utf-8')).hexdigest()
                },
                'contract_cross': inter_config['contract_cross'],
                'server_nodes': [
                    {
                        'host': node['host'],
                        'port': node['port'],
                        'username': node['username'],
                        'password': node['password']
                    } for node in useful_servers
                ]
            }

    def buildzone_process(self, gover_config: dict, inter_config: dict, zone_id: str, **kwargs):
        # TODO 先检查是否已经建立过
        gover_scripttool = tool_selector.selector(chain_type=gover_config['chain_type'])
        zone_info = gover_scripttool.queryZone(gover_config=gover_config, zone_id=zone_id)
        zone_info = [zone_id, ] + list(zone_info)
        inter_scripttool = tool_selector.selector(chain_type=zone_info[2])
        inter_chain_config = inter_scripttool.generate_interchain_config(inter_config, zone_info)

        # prestart
        inter_chain_config = inter_scripttool.pre_start(chain_config=inter_chain_config)
        # start chain
        inter_chain_config = inter_scripttool.start_chain(chain_config=inter_chain_config)
        time.sleep(5)
        # start mining
        inter_chain_config = inter_scripttool.start_mining(chain_config=inter_chain_config)

        # 更新互联链的rpc列表
        gover_scripttool.update_zone_rpc(inter_config=inter_chain_config, gover_config=gover_config)

        # create default account
        inter_chain_config = inter_scripttool.create_default_account(chain_config=inter_chain_config)

        # 部署跨链合约
        inter_chain_config = inter_scripttool.deploy_parallel_contract(chain_config=inter_chain_config)

        inter_scripttool.update_zone_crossctr_on_gover(chain_config=inter_chain_config, gover_config=gover_config)

        return inter_chain_config

    def buildzone_confirm(self, gover_config: dict, inter_chain_config: dict, **kwargs):
        master_node = gover_config['server_nodes'][0]
        default_account = master_node['default_account']
        account_address, account_password = default_account['address'], default_account['password']
        rpc = 'http://{host}:{rpcport}'.format(host=master_node['host'], rpcport=master_node['rpcport'])
        sdk = EthSdk(rpc, poa=True)
        sdk.defaultAccount = account_address
        sdk.unlockAccount(sdk.defaultAccount, account_password, 0)
        ctt_addr = gover_config['contract']['contracts']['Zone']['address'] 
        ctt_abi  = json.loads(gover_config['contract']['contracts']['Zone']['abistr'])
        inter_scripttool = tool_selector.selector(chain_type=inter_chain_config['chain_type'])
        inter_crossinfo = inter_scripttool.get_crossctr_info(inter_chain_config)
        self.print_func("crossinfo length: {}".format(len(inter_crossinfo)))
        tx_receipt, _ = sdk.contract_transact(
            contract_address=ctt_addr, 
            contract_abi=ctt_abi, 
            exec_func='alreadybuild', 
            func_args=[
                inter_chain_config['chain_id'], 
                inter_crossinfo
            ],
            source_args={
                'gas': 50000000
            }
        )
        txhash, status = tx_receipt['transactionHash'].hex(), tx_receipt['status']
        if status == 1:
            self.print_func("BUILDZONE result confirmation on chain SUCCEED, txhash[alreadybuild]: {}".format(txhash))
        else:
            self.print_func("BUILDZONE result confirmation on chain FAILED, txhash[alreadybuild]: {}".format(txhash))                

    def buildzone_listen(self, chain_config: dict, inter_config: dict, **kwargs):
        ispoa = True
        master_node = chain_config['server_nodes'][0]
        default_account = master_node['default_account']
        account_address, account_password = default_account['address'], default_account['password']
        rpc = 'http://{host}:{rpcport}'.format(host=master_node['host'], rpcport=master_node['rpcport'])
        sdk = EthSdk(rpc, poa=ispoa)
        sdk.defaultAccount = account_address
        sdk.unlockAccount(sdk.defaultAccount, account_password, 0)
        ctt_addr = chain_config['contract']['contracts']['Zone']['address'] 
        ctt_abi  = json.loads(chain_config['contract']['contracts']['Zone']['abistr'])
        
        def _check_buildzone(receipt, transaction):
            """
            1. get zoneid and gateway from the event[generate_zone] 
            2. generate one zone
            3. send tx: function[alreadybuild]. confirm on gover-chain
            """
            # logger.info("-----check buildzone")
            if str(receipt['to']).lower() != str(ctt_addr).lower(): return
            event_buildzone = 'genzone'
            events = sdk.parseEventFromContractMeta(
                contract_addr=ctt_addr,
                contract_abi=ctt_abi,
                tx_receipt=receipt,
                event_names=[event_buildzone]
            )
            result = events.get(event_buildzone, None)
            if result:
                result = result[-1]
                zchain_id = result['zoneID']
                self.print_func("find one GENERATE_ZONE event, block({}), txhash({}), zchain_id: {}".format(receipt['blockNumber'], receipt['transactionHash'].hex(), zchain_id))
                inter_chain_config = self.buildzone_process(chain_config, inter_config, zchain_id)
                self.print_func("准备向链上发起表明 <建域成功> 的交易......")
                self.buildzone_confirm(gover_config=chain_config, inter_chain_config=inter_chain_config)
                return inter_chain_config
            else:
                return None

        # main entry of loop_check function
        self.print_func("check contract({})...".format(ctt_addr))
        last_block_number = kwargs.get('last_block_number', 0)
        while True:
            blocks, last_block_number = self.get_latest_confirmed_blocks(chain_config, last_block_number)
            self.print_func('get latest {} blocks'.format(len(blocks)))
            for idx,block in enumerate(blocks):
                # logger.info("deal with block: {}".format(block['number']))
                if block['number'] % 100 == 0: 
                    self.print_func("block checkpoint: {}".format(block['number']))
                for idx, txhash in enumerate(block['transactions']):
                    receipt = sdk.w3.eth.getTransactionReceipt(txhash)
                    tran = sdk.w3.eth.getTransaction(txhash)
                    inter_chain_config = _check_buildzone(receipt, tran)
                    if inter_chain_config is not None:
                        return inter_chain_config, last_block_number
                time.sleep(0.1)
            if len(blocks) == 0:
                time.sleep(3)
            else:
                time.sleep(0.1)
            
    def buildzone_wait_confirm(self, chain_config, zone_id):
        ispoa = True
        chainid = int(zone_id)
        master_node = chain_config['server_nodes'][0]
        rpc = 'http://{host}:{rpcport}'.format(host=master_node['host'], rpcport=master_node['rpcport'])
        sdk = EthSdk(rpc,poa=ispoa)
        ctt_addr = chain_config['contract']['contracts']['Zone']['address'] 
        ctt_abi  = json.loads(chain_config['contract']['contracts']['Zone']['abistr'])
        starttime = time.time()
        timeout = 360
        while True:
            state = sdk.contract_call(
                contract_address=ctt_addr,
                contract_abi=ctt_abi,
                exec_func='queryZoneState',
                func_args=[chainid]
            )
            if state:
                return
            else:
                # require(time.time() - starttime < timeout, "wait accepted timeout !")
                self.print_func("查询域状态为: {}".format(state))
                time.sleep(5)


    def buildzone_issue(self, gover_chain: dict, delegate_account: dict, zone_args: tuple, **kwargs):
        print("检查是否已经成功发起建域请求......")
        ispoa = True
        gover_rpc = 'http://{}:{}'.format(gover_chain['server_nodes'][0]['host'], gover_chain['server_nodes'][0]['rpcport'])
        gover_contract_addr = gover_chain['contract']['contracts']['Zone']['address']
        gover_contract_abi = json.loads(gover_chain['contract']['contracts']['Zone']['abistr'])
        contract_info = (gover_contract_addr, gover_contract_abi)
        sdk = EthSdk(gover_rpc,poa=ispoa)
        _id = sdk.contract_call(
            contract_address=contract_info[0],
            contract_abi=contract_info[1],
            exec_func='queryZoneId',
            func_args=zone_args
        )
        if _id > 0:
            self.print_func("已成功发起过建域请求, zoneid: {}".format(_id))
            return _id
        self.print_func("未曾发起建域请求, 将发起建域请求......")
        privatekey = sdk.w3.eth.account.decrypt(delegate_account['key_filecontent'], delegate_account['password']).hex()
        receipt, events = sdk.sendrawTransaction(
            contract_address=Web3.toChecksumAddress(contract_info[0]),
            contract_abi=contract_info[1],
            exec_func='generateZone',
            func_args=zone_args,
            source_args={
                'from': Web3.toChecksumAddress(delegate_account['address']),
                'hitchain': ispoa,
                'privatekey': privatekey
            },
            event_names=['genzone', 'votehash', 'errinfo']
        )
        self.print_func(events)
        
        require(receipt['status'] == 1, "tx execution failed! txhash: {}".format(receipt['transactionHash']))
        if events.get('genzone', None):
            self.print_func("event[genzone]: {}".format(events['genzone'][-1]))
            zchainid = events['genzone'][-1]['zoneID']
            require(zchainid > 0, "zchainid({}) is invalid! ".format(zchainid))
            self.print_func("建域申请结果: 已获取到新建域信息 !")
            return int(zchainid)
        if events.get('errinfo', None):
            errinfo = events['errinfo'][-1]
            self.print_func("event[errinfo]: code: {}, msg: {}".format(errinfo['code'], errinfo['msg']))
            return 0
        if events.get('votehash', None):
            voteHash = events['votehash'][-1]
            self.print_func("event[votehash]: voteHash: {}, sender: {}".format(voteHash['voteHash'].hex(), voteHash['voter'].hex()))
            return 0

    def buildzone(self, chain_config: dict, gover_config: dict, zone_args: tuple, **kwargs):
        gover_scripttool = tool_selector.selector(chain_type=gover_config['chain_type'])
        server_nodes = chain_config['server_nodes']
        zone_id = 0
        for idx_node, node in enumerate(server_nodes):
            if not node['isdelegate']: continue
            zone_id = gover_scripttool.buildzone_issue(gover_config, node['delegate_account_on_gover'], zone_args)
            if zone_id != 0: break
        # if zone_id != 0 and zone_id not in chain_config['zone_id']:
        #     chain_config['zone_id'].append(zone_id)
        return zone_id

    def queryZone(self, gover_config: dict, zone_id: int):
        gover_node = gover_config['server_nodes'][0]
        gover_rpc = 'http://{}:{}'.format(gover_node['host'], gover_node['rpcport'])
        gover_sdk = EthSdk(gover_rpc, poa=True)
        gover_base = gover_config['contract']['contracts']['Zone']
        result = gover_sdk.contract_call(
            contract_address=gover_base['address'],
            contract_abi=json.loads(gover_base['abistr']),
            exec_func='queryZone',
            func_args=[int(zone_id)]
        )
        return result

    def get_rpcs(self, chain_config: dict) -> list:
        rpcaddrs = []
        for idx_node, node in enumerate(chain_config['server_nodes']):
            rpc_addr = 'http://{}:{}'.format(node['host'], node['rpcport'])
            rpcaddrs.append(rpc_addr)
        return rpcaddrs

    def update_zone_rpc(self, inter_config: dict, gover_config: dict):
        inter_scripttool = tool_selector.selector(chain_type=inter_config['chain_type'])
        rpcaddrs = inter_scripttool.get_rpcs(inter_config)
        zone_id = inter_config['chain_id']
        print("准备在治理链上更新域rpcaddr信息({})......".format(rpcaddrs))
        server_node = gover_config['server_nodes'][0]
        main_rpc_addr = 'http://{}:{}'.format(server_node['host'], server_node['rpcport'])
        sdk = EthSdk(main_rpc_addr, poa=True)
        default_account = server_node['default_account']
        sdk.defaultAccount = default_account['address']
        sdk.unlockAccount(sdk.defaultAccount,default_account['password'])
        contract_base = gover_config['contract']['contracts']['Zone']
        # private_key = sdk.w3.eth.account.decrypt(json.loads(zone_account['key_filecontent']), password=zone_account['password'])
        receipt, events = sdk.contract_transact(
            contract_address=contract_base['address'],
            contract_abi=json.loads(contract_base['abistr']),
            exec_func='updateZoneRpcs',
            func_args=[int(zone_id), rpcaddrs]
        )
        txhash = receipt['transactionHash']
        require(receipt['status'] == 1, "update_zone_rpc execution failed! txhash: {}".format(txhash))
        print("更新完成 !")

    def update_zone_crossctr(self, chain_config: dict, ctr_info: tuple):
        gover_node = chain_config['server_nodes'][0]
        gover_rpc = 'http://{}:{}'.format(gover_node['host'], gover_node['rpcport'])
        gover_base = chain_config['contract']['contracts']['Zone']
        gover_sdk = EthSdk(gover_rpc, poa=True)
        self.print_func("------ 正在治理链上更新域的跨链基础服务合约......")
        receipt, _ = gover_sdk.contract_transact(
            contract_address=gover_base['address'],
            contract_abi=json.loads(gover_base['abistr']),
            exec_func='updateZoneCross',
            func_args=ctr_info
        )
        require(receipt["status"] == 1, "updateZoneCross failed!")
        self.print_func("在治理链上更新域的跨链合约地址 {}".format("成功" if receipt['status'] == 1 else "失败"))

    def update_zone_crossctr_on_gover(self, chain_config, gover_config, **kwargs):
        cross_info = strjoin_helper.join(
            [
                chain_config['contract_cross']['ManagerGateway']["address"],
                chain_config['contract_cross']['ManagerGateway']["abistr"]
            ]
        )
        gover_scripttool = tool_selector.selector(chain_type=gover_config['chain_type'])
        gover_scripttool.update_zone_crossctr(gover_config, ctr_info=(int(chain_config['chain_id']), cross_info))
        return chain_config

    def transfer(self, node, account_from=None, account_to=None, value=0, unit='wei'):
        if value == 0: return
        rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        ethsdk = EthSdk(rpc, poa=True)
        if unit != 'wei':
            value = ethsdk.toWei(value, unit=unit)
        account_from = node['default_account'] if account_from is None else account_from
        ethsdk.unlockAccount(account_from['address'], account_from['password'])
        tx_receipt = ethsdk.sendSingleTransaction(
            addr_from=account_from['address'],
            addr_to=ethsdk.w3.toChecksumAddress(account_to['address']),
            value=value
        )
        require(tx_receipt['status'] == 1, "transfer from {} to {} failed!".format(
            account_from['address'],
            account_to['address'],
        ))