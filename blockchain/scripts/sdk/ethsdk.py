import time, os, sys
sys.path.append(os.path.abspath('.'))
from web3 import Web3, HTTPProvider
from web3.logs import STRICT, IGNORE, DISCARD, WARN
from web3.middleware import geth_poa_middleware
from eth_typing import HexStr
from solc import compile_standard
from functools import wraps
import argparse
import json, traceback


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
    """
    对于交易性函数，提前判断from账户是否已经解锁，但是不提供解锁功能
    """
    def __init__(self, url, name=None, poa=False):
        self.w3 =  Web3(HTTPProvider(url, {'timeout': 1000}))
        self.name = name if name else "unknown{}".format(int(time.time()*1000))
        self.__wait_timeout = 100000
        self.cache_compile_dir = 'cache'        
        # self.w3.eth.getBlock()
        self.__poa = poa
        if self.__poa:             
            self.__unlockSigners()
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.__unlockGenesis()        
        self.defaultAccount = self.genesisAccount
    
    @property
    def is_poa(self):
        return self.__poa

    def __unlockGenesis(self):
        print("unlock genesis account...")
        self.unlockAccount(account=self.genesisAccount,duration=0)
        
    def __unlockSigners(self):
        print("unlock signer account...")
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
                }
            },
            "libraries": libraries
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
    def deploy(self, abi, bytecode, constructor_args=None, transact_args=None):
        """
        return address, json.dumps(abi)
        """
        print("deploying contract......")
        if constructor_args is None: constructor_args = []
        if transact_args is None: transact_args = {}
        if not transact_args.get('from'): transact_args['from'] = self.defaultAccount
        # if not transact_args.get('gas'): transact_args['gas'] = 9000
        if not transact_args.get('gas_price'): transact_args['gas_price'] = 1
        pre_contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = pre_contract.constructor(*constructor_args).transact(transact_args)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=self.wait_timeout)
        address = tx_receipt.contractAddress
        return address, json.dumps(abi)
    
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
        account = self.w3.toChecksumAddress(account)
        flag = self.w3.geth.personal.unlock_account(account, password, duration)
        return flag
    
    def newAccount(self, password=""):
        return self.w3.geth.personal.newAccount(password)

    def getAccountBalance(self, addr):
        addr = self.w3.toChecksumAddress(addr)
        return self.w3.eth.getBalance(addr)

    @recordTime
    def sendSingleTransaction(self, addr_from, addr_to, value, gas=8000000, gas_price=1, authority=None):
        """发送交易，面向资金转移交易

        Returns:
            class TxReceipt => 交易执行的收据
        """
        tx = {'from': addr_from, 'to': addr_to, 'value': value, 'gas': gas, 'gas_price': gas_price}
        if authority: tx['authority'] = authority
        tx_hash = self.w3.eth.sendTransaction(tx)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=100000)
        return tx_receipt
      
    def parseEvent(self, contract, tx_receipt, event_names):
        """解析合约中的事件

        Returns:
            {} => key: 事件名称, value: 事件的值
        """
        eventArgsInfo = {}
        if event_names == '*':
            for event in contract.events:
                eventName = event.event_name
                myevents = contract.events[eventName]().processReceipt(txn_receipt=tx_receipt, errors=WARN)
                eventArgsInfo[eventName] = [dict(myevent['args']) for myevent in myevents]
        elif isinstance(event_names, list) and len(event_names) > 0:
            for eventName in event_names:
                myevents = contract.events[eventName]().processReceipt(txn_receipt=tx_receipt, errors=WARN)
                eventArgsInfo[eventName] = [dict(myevent['args']) for myevent in myevents]
        else:
            raise Exception("event names should be a list or '*'")
        return eventArgsInfo
    
    def parseEventFromContractMeta(self, contract_addr, contract_abi, tx_receipt, event_names):
        contract = self.w3.eth.contract(address=contract_addr, abi=contract_abi)
        return self.parseEvent(contract, tx_receipt, event_names)
        

    # @formatExceptionReturn
    @recordTime
    def contract_transact(self, contract_address, contract_abi, exec_func, func_args=None, source_args=None, event_names=None):
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
        # print("tx_hash: {}".format(tx_hash.hex()))
        tx_receipt = self.w3.eth.waitForTransactionReceipt(tx_hash, timeout=100000)
        eventArgsInfo = self.parseEvent(contract=contract, tx_receipt=tx_receipt, event_names=event_names)
        return tx_receipt, eventArgsInfo

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
        contract = self.w3.eth.contract(address=self.w3.toChecksumAddress(contract_address), abi=contract_abi)
        result = contract.functions[exec_func](*func_args).call(source_args)
        return result
    
    def parse_input(self, contract_address, contract_abi, func_input: HexStr) -> dict:
        contract = self.w3.eth.contract(address=self.w3.toChecksumAddress(contract_address), abi=contract_abi)
        return contract.decode_function_input(func_input)

    def toWei(self, value, unit='ether'):
        return self.w3.toWei(value,unit)

    @property
    def defaultAccount(self):
        if not self.w3.eth.defaultAccount:
            self.w3.eth.defaultAccount = self.w3.eth.accounts[0] 
        return self.w3.toChecksumAddress(self.w3.eth.defaultAccount)
    
    @defaultAccount.setter
    def defaultAccount(self, account):
        self.w3.eth.defaultAccount = self.w3.toChecksumAddress(account)
    
    @property
    def genesisAccount(self):
        if self.__poa:
            for account in self.w3.eth.accounts:
                auth = self.getAuthority(account)
                if auth == AUTH_SUPER:
                    return self.w3.toChecksumAddress(account)
            raise Exception("super account not found")
        else:
            return self.w3.toChecksumAddress(self.w3.eth.accounts[0])
        
    
    def getAuthority(self, account):
        return self.w3.manager.request_blocking(
            "eth_getAuthority",
           [self.w3.toChecksumAddress(account),self.w3.eth.defaultBlock]
        )

    def getSigners(self):
        return self.w3.manager.request_blocking("clique_getSigners",[])
    
    @property
    def signerFirst(self):
        signers = self.getSigners()
        if len(signers): return self.w3.toChecksumAddress(signers[0])
        raise Exception("there is no signer")
    



if __name__ == "__main__":
    # import sys, os
    # sys.path.append(os.path.abspath('.'))
    # from utils.chain.config import CHAINCONFIG
    # charityConfig = CHAINCONFIG['charity']
    # contract = charityConfig['contract']['charity']
    # myeth = HitSdk(url=charityConfig['url'], name="node1", poa=True)
    pass