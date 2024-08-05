import time, os, sys
from typing import overload
sys.path.append(os.path.abspath('.'))
from web3 import Web3, HTTPProvider
from web3._utils.transactions import fill_nonce
from web3._utils.empty import (
    empty,
)
from web3.logs import STRICT, IGNORE, DISCARD, WARN
from web3.middleware import geth_poa_middleware
from solc import compile_standard
from functools import wraps
import argparse
import json, traceback
from tools.helper import strjoin_helper as strjoin

AUTH_SUPER = hex(2**255)

def recordTime(func):
    @wraps(func)
    def func_wraps(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print("{} run for about: {:.6f}s".format(func.__name__, (end-start)))
        return result
    return func_wraps

class ContractExecType:
    CONTRACT_CALL = 0
    CONTRACT_TRAN = 1

def savefile(filepath, content):
    dir_path = os.path.dirname(os.path.abspath(filepath))
    if not isinstance(content, str): content = str(content)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(filepath, 'w') as f:
        f.write(content)

class EthSdk(object):
    def __init__(
        self, 
        url, 
        name=None, 
        poa=False, 
        hit=False,
        unlock_genesis=True, 
        **kwargs
        # kwargs 的使用值
        # provider_timeout = 1000
    ):
        self.w3 =  Web3(HTTPProvider(url, {'timeout': kwargs.get("provider_timeout", 1000)}))
        self.name = name if name else "unknown{}".format(int(time.time()*1000))
        self.__wait_timeout = 100000
        self.cache_compile_dir = 'cache'        
        # self.w3.eth.getBlock()
        self.__poa = poa
        self.__hit = hit
        if self.__poa or self.__hit:             
            # if unlock_signers: self.__unlockSigners()
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        if unlock_genesis: self.__unlockGenesis()        
        self.defaultAccount = self.genesisAccount
    
    @property
    def is_poa(self):
        return self.__poa

    def __unlockGenesis(self):
        flag = self.unlockAccount(account=self.genesisAccount,duration=0)
        print("解锁 genesis account, result: {}".format(flag))
        
    def __unlockSigners(self):
        signers = self.getSigners()
        for signer in signers:
            self.unlockAccount(signer,duration=0)

    @recordTime
    def compile(self, contract_filename, libraries=None, **kwargs):
        """
        return dict
        contract_info[contract_name] = {'abi': abi, 'bytecode': bytecode}
        """
        print("compiling contract......")
        with open(contract_filename, 'r') as f:
            contract_content = f.read()
        # 首先从cache里面获取结果
        cache_file = os.path.join(self.cache_compile_dir, os.path.basename(contract_filename)+"_cache")
        cache_result = os.path.join(self.cache_compile_dir, os.path.basename(contract_filename)+"_cache_result")
        if os.path.exists(cache_file) and os.path.exists(cache_result): 
            with open(cache_file, 'r') as f:
                cache_content = f.read()
                if cache_content == contract_content:
                    print("compile result using cache: {}".format(cache_result))
                    return json.load(open(cache_result, 'r'))
                else:
                    print("find no cache!")
        if not libraries: libraries = {}
        compiled_sol = compile_standard({
            "language": "Solidity",
            "sources": {
                contract_filename: {
                    "content": """{}
                    """.format(contract_content)
                }
            },
            "settings":{
                "optimizer": {
                    "enabled": True,
                    "runs": 500
                },
                "outputSelection": {
                    "*": {
                        "*": [
                            "metadata", "evm.bytecode"
                            , "evm.bytecode.sourceMap"
                        ]
                    }
                },
                "libraries": libraries,
                # "viaIR": True,
            },
            
        }, **kwargs)
        # 一个文件里面可能会有多个合约
        contract_group = compiled_sol['contracts'][contract_filename]
        contract_info = {}
        for contract_name, value in contract_group.items():
            bytecode = value['evm']['bytecode']['object']
            abi = json.loads(value['metadata'])['output']['abi']
            contract_info[contract_name] = {'abi': abi, 'bytecode': bytecode}
        
        # 写入本地cache
        savefile(cache_result,json.dumps(contract_info))
        savefile(cache_file, contract_content)
        
        return contract_info

    @property
    def wait_timeout(self):
        return self.__wait_timeout
    
    @wait_timeout.setter
    def wait_timeout(self, timeout):
        self.__wait_timeout = timeout


    def build_transaction_args(self):
        #TODO 构建交易参数，方便构建
        ...

    @recordTime
    def deploy(self, abi, bytecode, constructor_args=None, transact_args=None, wait=True):
        """
        return address, json.dumps(abi)
        """
        print("deploying contract......")
        if constructor_args is None: constructor_args = []
        if transact_args is None: transact_args = {}
        if not transact_args.get('from'): transact_args['from'] = self.defaultAccount
        if not transact_args.get('gas_price'): transact_args['gas_price'] = 1
        pre_contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = pre_contract.constructor(*constructor_args).transact(transact_args)
        print("waiting receipt....")
        info = ''
        if wait:
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=self.wait_timeout)
            info = tx_receipt.contractAddress
        else:
            info = tx_hash.hex()
        return info, json.dumps(abi)
        
    @recordTime
    def deployByPrivateKey(self, abi, bytecode, transact_args, constructor_args=None):
        if constructor_args is None: constructor_args = []
        private_key = transact_args['private_key']
        addr_from = self.w3.to_checksum_address(transact_args['from'])

        pre_contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        constructor = pre_contract.constructor(*constructor_args)
        gas = self.w3.eth.estimate_gas({'from': addr_from, 'to': b'', 'data': constructor.data_in_transaction})
        args = fill_nonce(self.w3, {'from': addr_from, 'gas': gas, 'chainId':None})
        deploy_transaction = constructor.build_transaction(args)
        if transact_args.get('hitchain', False):
            deploy_transaction['hitchain'] = True
            deploy_transaction['authority'] = "0x66"
        else:
            deploy_transaction['hitchain'] = False
        signtx = self.w3.eth.account.sign_transaction(deploy_transaction,private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signtx.rawTransaction)
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=100000)
        return tx_receipt.contractAddress
    
    def parse_input(self, contract_address, contract_abi, func_input):        
        try:
            contract_instance = self.w3.eth.contract(address=contract_address, abi=contract_abi)
            func, params = contract_instance.decode_function_input(func_input)
            
        except Exception as e:
            func, params = None, {}
        finally:
            return func, params


    # @formatExceptionReturn
    def compileAndDeploy(self, contractfile, contract_name, constructor_args=None, transact_args=None):
        """从contractfile中读取合约，进行简单的编译和部署

        Args:
            contractfile (str): 合约文件的路径

        Returns:
            (str, str) => (合约部署的地址, abi字符串)
        """
        if constructor_args is None: constructor_args = []
        if transact_args is None: transact_args = {}
        contract_info = self.compile(contractfile, allow_paths=os.path.abspath('.'))
        abi, bytecode = contract_info[contract_name]['abi'], contract_info[contract_name]['bytecode']
        addr, abistr = self.deploy(abi=abi, bytecode=bytecode, constructor_args=constructor_args, transact_args=transact_args)
        print("compileAndDeploy contract succeeded!")
        return addr, abistr
    
    def unlockAccount(self, account, password="", duration=300):
        account = self.w3.to_checksum_address(account)
        if self.getAccountStatus(account):
            return True
        flag = self.w3.geth.personal.unlock_account(account, password, duration)
        return flag

    def getAccountStatus(self, account):
        account = self.w3.to_checksum_address(account)
        wallets = self.w3.geth.personal.list_wallets()
        for wallet in wallets:
            for account in wallet['accounts']:
                if self.w3.to_checksum_address(account['address']) == account:
                    return wallet['status'] == "Unlocked"
        return False
    
    def newAccount(self, password=""):
        address = self.w3.geth.personal.new_account(password)
        return self.w3.to_checksum_address(address)

    def getAccountBalance(self, addr):
        addr = self.w3.to_checksum_address(addr)
        return self.w3.eth.get_balance(addr)
    
    # @formatExceptionReturn
    @recordTime
    def sendSingleTransaction(self, addr_from, addr_to, value, gas=8000000, gas_price=1, authority=None, wait=True):
        """发送交易，面向资金转移交易

        Returns:
            class TxReceipt => 交易执行的收据
        """
        tx = {
            'from': self.w3.to_checksum_address(addr_from), 
            'to': self.w3.to_checksum_address(addr_to), 
            'value': value, 
            'gas': gas, 
            'gasPrice': gas_price,
            'chainId': self.w3.eth.chain_id
        }
        if authority: tx['authority'] = authority
        tx_hash = self.w3.eth.send_transaction(tx)
        if not wait: 
            return tx_hash
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=100000)
        return tx_receipt
    
    def sendSingleRawTransaction(self, addr_from, addr_to, value, gas=8000000, gas_price=1, authority=None, wait=True,source_args=None):
        """发送交易，面向资金转移交易

        Returns:
            class TxReceipt => 交易执行的收据
        """
        if source_args is None: source_args = {}
        payload = {}
        payload['nonce'] = source_args.get('nonce', self.w3.eth.get_transaction_count(addr_from))
        payload['gasPrice'] = self.w3.eth.gas_price
        payload['gas'] = gas
        payload['value'] = value  
        payload['to'] = addr_to
        if 'hitchain' in source_args and source_args['hitchain']:
            payload['hitchain'] = True
            payload['authority'] = "0x66"
        else:
            payload['hitchain'] = False
        print("[-EthSdk-] 签名交易")
        signtx = self.w3.eth.account.sign_transaction(payload,source_args['privatekey'])
        print("[-EthSdk-] 发送交易")
        tx_hash = self.w3.eth.send_raw_transaction(signtx.rawTransaction)
        if not wait:
            return tx_hash
        print("[-EthSdk-] 等待回执")
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=100000)
        print("[-EthSdk-] 交易完成")
        return tx_receipt




        tx = {'from': self.w3.toChecksumAddress(addr_from), 'to': self.w3.toChecksumAddress(addr_to), 'value': value, 'gas': gas, 'gasPrice': gas_price}
        if authority: tx['authority'] = authority
        tx_hash = self.w3.eth.sendTransaction(tx)
        if not wait: 
            return tx_hash
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=100000)
        return tx_receipt
    
    def sendrawTransaction(self,
                           contract_address,
                           contract_abi,
                           exec_func,
                           func_args=None,
                           source_args=None, 
                           event_names=None,
                           wait = True,
        ):
        '''''
        TOCheck
        
        '''''
        if func_args is None: func_args = []
        if source_args is None: source_args = {}
        if event_names is None: event_names = []
        contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        abi_data = contract.encode_abi(fn_name = exec_func,args=func_args)
        addr_from = self.w3.to_checksum_address(source_args['from'])
        if 'value' not in source_args:
            value_data = 0
        else:
            value_data = int(source_args['value'])
        gas_data = source_args.get('gas', None)
        if not gas_data:
            transForEstimateGas = {}
            transForEstimateGas['from'] = addr_from
            transForEstimateGas['to'] = contract_address
            transForEstimateGas['data'] = abi_data
            transForEstimateGas['value'] = value_data
            # print("estimateGas......")
            gas_data = self.w3.eth.estimate_gas(transForEstimateGas)
        payload = {}
        # payload['from'] = source_args['from']
        payload['nonce'] = source_args.get("nonce", self.w3.eth.get_transaction_count(addr_from))
        payload['gasPrice'] = 1
        payload['gas'] = gas_data
        payload['value'] = value_data  
        payload['to'] = contract_address
        payload['data'] = abi_data
        payload['chainId'] = self.w3.eth.chain_id
        # payload['chainId'] = 31317
        # payload['chainId'] = 21
        # payload['authority'] = "0x66"
        if self.__hit:
            if 'hitchain' in source_args and source_args['hitchain']:
                payload['hitchain'] = True
                payload['authority'] = "0x66"
            else:
                payload['hitchain'] = False
        # print("[-EthSdk-] 签名交易")
        signtx = self.w3.eth.account.sign_transaction(payload,source_args['privatekey'])
        # print("[-EthSdk-] 发送交易")
        tx_hash = self.w3.eth.send_raw_transaction(signtx.rawTransaction)
        # print("[-EthSdk-] 交易完成")
        if wait:
            # print("[-EthSdk-] 等待回执")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=100000)
            eventArgsInfo = self.parseEvent(contract=contract, tx_receipt=tx_receipt, event_names=event_names)
            # print("[-EthSdk-] 获得回执")
            return tx_receipt, eventArgsInfo
        else:
            return tx_hash, None
    
    def sendrawTransaction_usual(self,cross_ctr,exec_func,func_args=None,source_args=None, event_names=None):
        address, abistr = strjoin.dejoin(cross_ctr)
        return self.sendrawTransaction(
            contract_address=address,
            contract_abi=json.loads(abistr),
            exec_func=exec_func,
            func_args=func_args,
            source_args=source_args,
            event_names=event_names
        )

    def parseEventFromContractMeta(self, contract_addr, contract_abi, tx_receipt, event_names):
        contract_instance = self.w3.eth.contract(address=contract_addr, abi=contract_abi)
        return self.parseEvent(contract=contract_instance,tx_receipt=tx_receipt,event_names=event_names)

    # @formatExceptionReturn
    def parseEvent(self, contract, tx_receipt, event_names):
        """解析合约中的事件

        Returns:
            {} => key: 事件名称, value: 事件的值
        """
        eventArgsInfo = {}
        if not event_names: return eventArgsInfo
        if event_names == '*':
            for event in contract.events:
                eventName = event.event_name
                myevents = contract.events[eventName]().process_receipt(txn_receipt=tx_receipt, errors=WARN)
                eventArgsInfo[eventName] = [dict(myevent['args']) for myevent in myevents]
        elif isinstance(event_names, list):
            for eventName in event_names:
                myevents = contract.events[eventName]().process_receipt(txn_receipt=tx_receipt, errors=WARN)
                eventArgsInfo[eventName] = [dict(myevent['args']) for myevent in myevents]
        else:
            raise Exception("eventNames should be list or '*'")
        return eventArgsInfo
        
    # @formatExceptionReturn
    # @recordTime
    def contract_transact(self, contract_address, contract_abi, exec_func, func_args=None, source_args=None, event_names=None, wait=True):
        """执行合约交易
        TODO: 
        1. 先在abi中检测是否存在 func 和 event
        2. 执行交易前是否可以先验证一下：
            1. 当前账户的余额是否大于交易的gas
            2. 是否能执行成功
        Args:
            contract_address (str): 合约地址
            contract_abi (dict): 合约abi字典
            exec_func (str): 需要执行的函数
            func_args (list, optional): 需要执行的函数的参数列表. Defaults to [].
            source_args (dict, optional): 合约执行的参数字典，就是 transact()  的参数, Defaults to {}, 样例：{'from': '0xasdad...', 'to': '0xasdad...', 'value': 10, 'gas':90000, 'gas_price':123}
            event_name (list, optional): 事件名称列表. Defaults to [].
        Returns:
            (TxReceipt, {}) => (合约执行的收据，事件的返回值)
        """
        if func_args is None: func_args = []
        if source_args is None: source_args = {}
        if event_names is None: event_names = []
        contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        tx_hash = contract.functions[exec_func](*func_args).transact(source_args)
        if wait:
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=100000)
            eventArgsInfo = self.parseEvent(contract=contract, tx_receipt=tx_receipt, event_names=event_names)
            return tx_receipt, eventArgsInfo
        else:
            return tx_hash, None
    
    def contract_transact_usual(self, contract_info:str, exec_func:str, func_args=None, source_args=None, event_names=None):
        """通用型合约交易

        Args:
            contract_info (str): 经过strjoin编码的合约信息
            exec_func (str): 需要执行的函数
            func_args (list, optional): 需要执行的函数的参数列表. Defaults to None.
            source_args (dict, optional): 合约执行的参数字典，就是 transact()  的参数. Defaults to None.
            event_names (list, optional): 事件名称列表. Defaults to None.

        Raises:
            Exception: [description]
            Exception: [description]

        Returns:
            [type]: [description]
        """
        address, abistr = strjoin.dejoin(contract_info)
        return self.contract_transact(
            contract_address=address,
            contract_abi=json.loads(abistr),
            exec_func=exec_func,
            func_args=func_args,
            source_args=source_args,
            event_names=event_names
        )

    def contract_call(self, contract_address, contract_abi, exec_func, func_args=None, source_args=None):
        """执行合约交易
        TODO: 
        1. 先在abi中检测是否存在 func 和 event
        2. 执行交易前是否可以先验证一下：
            1. 当前账户的余额是否大于交易的gas
            2. 是否能执行成功
        Args:
            contract_address (str): 合约地址
            contract_abi (dict): 合约abi字典
            exec_func (str): 需要执行的函数
            func_args (list, optional): 需要执行的函数的参数列表. Defaults to [].
            source_args (dict, optional): 合约执行的参数字典，就是 transact()  的参数, Defaults to {}, 样例：{'from': '0xasdad...', 'to': '0xasdad...', 'value': 10, 'gas':90000, 'gas_price':123}
        Returns:
            result => 合约返回的结果，具体类型根据合约返回结果来确定
        """
        if func_args is None: func_args = []
        if source_args is None: source_args = {}
        contract = self.w3.eth.contract(address=self.w3.to_checksum_address(contract_address), abi=contract_abi)
        result = contract.functions[exec_func](*func_args).call(source_args)
        return result
    
    def contract_call_usual(self, contract_info: str, exec_func: str, func_args=None, source_args=None):
        """通用型合约查询

        Args:
            contract_info (str): strjoin编码后的字符串
            exec_func (str): 执行函数
            func_args (list): [description]. 需要执行的函数的参数列表. Defaults to None.
            source_args (doct): [description]. 合约执行的参数字典，就是 transact()  的参数, Defaults to None,
        """
        address, abistr = strjoin.dejoin(contract_info)
        return self.contract_call(contract_address=address, contract_abi=json.loads(abistr),exec_func=exec_func,func_args=func_args,source_args=source_args)


    def toWei(self, value, unit='ether'):
        return self.w3.to_wei(value,unit)

    @property
    def defaultAccount(self):
        if not self.w3.eth.default_account:
            self.w3.eth.default_account = self.w3.eth.accounts[0] 
        return self.w3.to_checksum_address(self.w3.eth.default_account)
    
    @defaultAccount.setter
    def defaultAccount(self, account):
        self.w3.eth.default_account = self.w3.to_checksum_address(account) if account else empty
    
    @property
    def genesisAccount(self):
        if self.__hit:
            for account in self.w3.eth.accounts:
                auth = self.getAuthority(account)
                if auth == AUTH_SUPER:
                    return self.w3.to_checksum_address(account)
            # raise Exception("super account not found")
            print("WARN: genesis account not found")
            return None
        else:
            return self.w3.to_checksum_address(self.w3.eth.accounts[0]) if self.w3.eth.accounts else None
            # return ""
        
    
    def getAuthority(self, account):
        return self.w3.manager.request_blocking(
            "eth_getAuthority",
           [self.w3.to_checksum_address(account),self.w3.eth.default_block]
        )

    def getSigners(self):
        return self.w3.manager.request_blocking("clique_getSigners",[])
    
    def propose_signer(self, address, auth=True):
        return self.w3.manager.request_blocking("clique_propose", [address, auth])

    @property
    def signerFirst(self):
        accounts = [str(account).lower() for account in self.w3.eth.accounts]
        signers = [ signer for signer in  self.getSigners() if str(signer).lower() in accounts]
        if len(signers): 
            return self.w3.to_checksum_address(signers[0])
        raise Exception("there is no signer")
    
    def waitForTransactionReceipt(self, txhash, timeout=300):
        receipt = None
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(txhash, timeout=timeout)
        except Exception as e:
            raise Exception("exception: {}\n-----receipt: {}".format(str(e), dict(receipt)))
        return receipt
    
    def get_contract(self, address: str, abi: dict):
        return self.w3.eth.contract(address=self.w3.to_checksum_address(address), abi=abi)

    def get_nonce(self, address: str=None):
        if not address:
            address = self.defaultAccount
        else:
            address = self.w3.to_checksum_address(address)
        return self.w3.eth.get_transaction_count(address, block_identifier="pending")


if __name__ == "__main__":
    # import sys, os
    # sys.path.append(os.path.abspath('.'))
    # from utils.chain.config import CHAINCONFIG
    # charityConfig = CHAINCONFIG['charity']
    # contract = charityConfig['contract']['charity']
    # myeth = HitSdk(url=charityConfig['url'], name="node1", poa=True)
    pass