import os, sys
import traceback, base58, ed25519, hashlib
import requests, json
sys.path.append(os.path.abspath('.'))

import time

BUBI_ALPHABET = b'123456789AbCDEFGHJKLMNPQRSTuVWXYZaBcdefghijkmnopqrstUvwxyz'
genesisAccountInfo = {'buQBBQuEEa1j5xM61oWprLXese8jFRTiSkyC':{\
                    'private_key':'privbtMJ88nvwcAppQNuLaB26EQa37Cmd3y4wBy3gFc6f1qXuoC5k2Mo', \
                    'public_key': 'b001abe98c85838cb9e48c64c3e2c3d3f4ef6cbe88571dfdb9471db2e83588d0374a714db749', \
                    'address': 'buQBBQuEEa1j5xM61oWprLXese8jFRTiSkyC'}}

def require(condition, msg="error"):
    if not condition:
        raise Exception(msg)
class BuSdk(object):
    TYPE_CREATE_ACCOUNT = 1
    TYPE_ISSUE_ASSET = 2
    TYPE_PAY_ASSET = 3
    TYPE_SET_METADATA = 4
    TYPE_PAY_COIN = 5
    TYPE_LOG = 6
    TYPE_SET_PRIVILEGE = 7

    PVK_PREFIX = 'DA379F'# params: generate account 
    PVK_VERSION = '01'
    PVK_FILL = '00'
    PBK_PREFIX = 'B0'
    PBK_VERSION = '01'
    ADDR_PREFIX = '0156'
    ADDR_VERSION = '01'

    def __init__(self, url, genesisAccountInfo=genesisAccountInfo): # {address:{'private_key':'', 'public_key': '', 'address': ''}}
        super().__init__()
        self.url = url
        self.accountDB = {}
        if isinstance(genesisAccountInfo,dict):
            self.accountDB.update(genesisAccountInfo)
        self.genesisAccount = self.getGenesisAccount()['result']['address']
        self.defaultAccount = self.genesisAccount
    
    def __checkArgs(self, source_address, fee_limit, gas_price, ceil_ledger_seq, transaction_type):
        if fee_limit <= 0: raise Exception("fee_limit shoule be larger than 0")
        if gas_price < 0: raise Exception("gas_price should be larger than 0 or equal to 0")
        if transaction_type not in [BuSdk.TYPE_CREATE_ACCOUNT, BuSdk.TYPE_ISSUE_ASSET, BuSdk.TYPE_PAY_ASSET, BuSdk.TYPE_SET_METADATA, BuSdk.TYPE_PAY_COIN, BuSdk.TYPE_LOG, BuSdk.TYPE_SET_PRIVILEGE]:
            raise Exception("unknown transaction type")

    # def __buildHead(self, source_address, nonce, fee_limit, gas_price, ceil_ledger_seq, metadata):
    #     if fee_limit <= 0: raise Exception("fee_limit shoule be larger than 0")
    #     if gas_price < 0: raise Exception("gas_price should be larger than 0 or equal to 0")
    #     transaction = Transaction()
    #     transaction.source_address = source_address
    #     transaction.nonce = nonce
    #     transaction.fee_limit = fee_limit
    #     transaction.gas_price = gas_price
    #     transaction.ceil_ledger_seq = ceil_ledger_seq
    #     if isinstance(metadata, str): metadata = metadata.encode()
    #     transaction.metadata = metadata
    #     return transaction
        
    # def __buildBlob_create_account(self, transaction_protobuf, operations: list):
    #     for oper in operations:
    #         # TODO 最好加一个字段检测
    #         operation = transaction_protobuf.operations.add()
    #         operation.type = Operation.Type.CREATE_ACCOUNT
    #         # operation.source_address = source_address
    #         # operation.metadata = metadata
    #         # 创建账户
    #         createaccount_req = oper
    #         operationcreateaccount = OperationCreateAccount()
    #         operationcreateaccount.dest_address = createaccount_req.get('dest_address', '')
    #         operationcreateaccount.init_balance = createaccount_req.get('init_balance', 0)
    #         operationcreateaccount.init_input = createaccount_req.get('init_input', '')
    #         # 创建合约 # removed 只创建地址账号，不创建合约账号，或者加个判断来做
    #         contract_req = createaccount_req.get('contract', {})
    #         contract = Contract()
    #         contract.type = Contract.ContractType.JAVASCRIPT
    #         contract.payload = contract_req.get('payload', '')
    #         operationcreateaccount.contract.CopyFrom(contract)

    #         priv_req = createaccount_req.get('priv', {})
    #         accountprivilege = AccountPrivilege()
    #         accountprivilege.master_weight = priv_req.get('master_weight', 0 if contract_req else 1) # 创建地址账号时，值为1, 创建合约账号时，值为0
    #         # 创建权限
    #         signers_req = priv_req.get('signers', [])
    #         for signer_req in signers_req:
    #             signer = accountprivilege.signers.add()
    #             signer.address = signer_req.get('address', '')
    #             signer.weight = signer_req.get('weight', 1)
            
    #         thresholds_req = priv_req.get('thresholds', {})
    #         thresholds = AccountThreshold()
    #         thresholds.tx_threshold = thresholds_req.get('tx_threshold', 1)
    #         # type_threshold 就不设置了吧

    #         accountprivilege.thresholds.CopyFrom(thresholds)
    #         operationcreateaccount.priv.CopyFrom(accountprivilege)
    #         # operationcreateaccount的metadatas也就不设置了吧，看上去也没啥用啊               
    #         operation.create_account.CopyFrom(operationcreateaccount)
    #     return transaction_protobuf

    # def buildBlob(self, source_address, nonce, fee_limit=100000000000, gas_price=1000, ceil_ledger_seq=0, metadata="", operations=[], transaction_type=0):
    #     try:
    #         # self.__checkArgs(source_address, fee_limit, gas_price, ceil_ledger_seq, transaction_type)
    #         transaction = self.__buildHead(source_address, nonce, fee_limit, gas_price, ceil_ledger_seq, metadata)
    #         # tx = self.__buildTransaction(source_address, fee_limit, gas_price, ceil_ledger_seq=0, metadata="", operations=None):
    #         if transaction_type == BuSdk.TYPE_CREATE_ACCOUNT:
    #             transaction_blob = self.__build_create_account(transaction, operations)
    #         # 后面这几项内容需要啥就写啥，一下子全写完也没啥用
    #         elif transaction_type == BuSdk.TYPE_ISSUE_ASSET:
    #             pass
    #         elif transaction_type == BuSdk.TYPE_PAY_ASSET:
    #             pass
    #         elif transaction_type == BuSdk.TYPE_SET_METADATA:
    #             pass
    #         elif transaction_type == BuSdk.TYPE_PAY_COIN:
    #             pass
    #         elif transaction_type == BuSdk.TYPE_LOG:
    #             pass
    #         elif transaction_type == BuSdk.TYPE_SET_PRIVILEGE:
    #             pass
    #         else:
    #             raise Exception("unknown transaction type")
    #         transaction_str = transaction_blob.SerializeToString().hex()
    #         return transaction_str, ''
    #     except Exception as e:
    #         print(traceback.format_exc())
    #         return None, str(e)

    def buildBlobFromSource(self, transaction):
        r = requests.post(
            self.__buildRpc("getTransactionBlob"),
            json.dumps(transaction)
        )
        result = r.json()
        require(result["error_code"] == 0, "build blob failed, result: {}".format(result))
        return result["result"]['hash'], result["result"]["transaction_blob"]
    
    def estimateFee(self, item):
        r = requests.post(
            self.__buildRpc("testTransaction"),
            json.dumps(item)
        )
        result = r.json()
        require(result["error_code"] == 0, "estimate fee failed, result: {}".format(result))
        return result['result']['txs'][0]['actual_fee']

    def __get_raw_private_key(self, private_key):
        # private_key_bytes = bytes(private_key)
        private_key = bytes(private_key, encoding='utf-8')
        private_key_bytes = base58.b58decode(private_key,alphabet=BUBI_ALPHABET)
        raw_private_bytes = private_key_bytes[4:-5]
        return raw_private_bytes

    def __parse_publickey_from_privatekey(self, private_key):
        raw_private_key = self.__get_raw_private_key(private_key)
        public_key = self.__create_public_key(raw_private_key)
        return public_key
    
    def __parse_address_from_privatekey(self, private_key):
        raw_private_key = self.__get_raw_private_key(private_key)
        address = self.__create_address(raw_private_key)
        return address

    def signTran(self, transaction_blob, private_key):
        """
        return [signiture: str, public_key: str]
        """
        transaction_blob_bytes = bytes.fromhex(transaction_blob)
        public_key = self.__parse_publickey_from_privatekey(private_key)
        raw_private_key = self.__get_raw_private_key(private_key)
        signiture = ed25519.SigningKey(bytes(raw_private_key)).sign(transaction_blob_bytes).hex()
        return signiture, public_key

    def __create_private_key(self, raw_private_key):
        prefix = bytes.fromhex(BuSdk.PVK_PREFIX)
        version = bytes.fromhex(BuSdk.PVK_VERSION)
        fill = bytes.fromhex(BuSdk.PVK_FILL)
        new = prefix + version + raw_private_key + fill
        one = hashlib.sha256(new).digest()
        two = hashlib.sha256(one).digest()
        new += two[0:4]
        private_key = base58.b58encode(new, alphabet=BUBI_ALPHABET)
        return private_key.decode()
    
    def checkPrivateKey(self, private_key):
        try:
            private_key = base58.b58decode(private_key, alphabet=BUBI_ALPHABET)
            prefix = bytes.fromhex(BuSdk.PVK_PREFIX)
            version = bytes.fromhex(BuSdk.PVK_VERSION)
            fill = bytes.fromhex(BuSdk.PVK_FILL)
            if private_key[0:3] != prefix: return False
            if private_key[3] != version[0]: return False
            if private_key[-5] != fill[0]: return False
            new = private_key[0:-4]
            one = hashlib.sha256(new).digest()
            two = hashlib.sha256(one).digest()
            if two[0:4] != private_key[-4:]: return False
            return True
        except:
            return False
    
    def __create_public_key(self, raw_private_key):
        pbkey = ed25519.SigningKey(raw_private_key)
        raw_public_key = pbkey.get_verifying_key().to_bytes()
        prefix = bytes.fromhex(BuSdk.PBK_PREFIX)
        version = bytes.fromhex(BuSdk.PBK_VERSION)
        new = prefix+version+raw_public_key
        one = hashlib.sha256(new).digest()
        two = hashlib.sha256(one).digest()
        new += two[0:4]
        public_key = new.hex()
        return public_key

    def checkPublicKey(self, publicKey):
        try:
            publicKey_bytes = bytes.fromhex(publicKey)
            prefix = bytes.fromhex(BuSdk.PBK_PREFIX)
            version = bytes.fromhex(BuSdk.PBK_VERSION)
            if publicKey_bytes[0] != prefix[0]: return False
            if publicKey_bytes[1] != version[0]: return False
            new = publicKey_bytes[0:-4]
            one = hashlib.sha256(new).digest()
            two = hashlib.sha256(one).digest()
            if two[0:4] != publicKey_bytes[-4:]: return False
        except:
            # print(traceback.format_exc())
            return False
        return True

    def __create_address(self, raw_private_key):
        pbkey = ed25519.SigningKey(raw_private_key)
        raw_public_key = pbkey.get_verifying_key().to_bytes()
        one = hashlib.sha256(raw_public_key).digest()
        # prefix = bytes.fromhex('F8E1') # bubi的文档里是这么写的，可以生成以 adx 开头的地址
        prefix = bytes.fromhex(BuSdk.ADDR_PREFIX) # bumo的文档里是这么写的，可以生成以 bu 开头的地址
        version = bytes.fromhex(BuSdk.ADDR_VERSION)
        new = prefix + version + one[-20:]
        one = hashlib.sha256(new).digest()
        two = hashlib.sha256(one).digest()
        new += two[0:4]
        address = base58.b58encode(new, alphabet=BUBI_ALPHABET)
        return address.decode()

    def checkAddress(self, address):
        try:
            # TODO 非空检测，长度检测，起始字符bu检测
            address = base58.b58decode(address, alphabet=BUBI_ALPHABET)
            prefix = bytes.fromhex(BuSdk.ADDR_PREFIX)
            version = bytes.fromhex(BuSdk.ADDR_VERSION)
            if address[0:2] != prefix: return False
            if address[2] != version[0]: return False # 这里要注意 [0]
            new = address[0:-4]
            one = hashlib.sha256(new).digest()
            two = hashlib.sha256(one).digest()
            if two[0:4] != address[-4:]: return False
        except:
            return False
        return True
    
    def storeAccount(self, account:dict):
        require(
            account.get('address', None) and 
            account.get('public_key', None) and
            account.get('private_key', None),
            "account must include address, public_key and private_key"
        )
        require(
            self.checkPrivateKey(private_key=account['private_key']),
            "private_key is invalid"
        )
        require(
            self.checkPublicKey(publicKey=account['public_key']),
            "public_key is invalid"
        )
        require(
            self.checkAddress(address=account['address']),
            "address is invalid"
        )

        publickey = self.__parse_publickey_from_privatekey(account['private_key'])
        require(publickey == account['public_key'], "public_key doesn`t match private_key")
        address = self.__parse_address_from_privatekey(account['private_key'])
        require(address == account['address'], "address doesn`t match private_key")
        self.accountDB.update({
            account['address']: account
        })
    
    def generateAccount(self):
        account = {'private_key':'', 'public_key': '', 'address': ''}
        err = ''
        try:
            raw_private_key = os.urandom(32)
            # get private key
            private_key = self.__create_private_key(raw_private_key)
            # get public_key
            public_key = self.__create_public_key(raw_private_key)
            # get address
            address = self.__create_address(raw_private_key)
            account['private_key'] = private_key
            account['public_key'] = public_key
            account['address'] = address
            self.accountDB.update({
                str(address):account
            })
        except Exception as e:
            print(traceback.format_exc())
            err = str(e)
        finally:
            return account, err

    def __buildRpc(self, method, params=None):
        require(isinstance(params,dict) or not params, "params format is wrong, params type: {}".format(type(params)))
        rpc = "{}/{}".format(self.url, method) + ("" if not params else "?{}".format("&".join("{}={}".format(str(k), str(v)) for k, v in params.items())))
        print("buildRpc: {}".format(rpc))
        return rpc


    # 查询类交易  创建创世账户  a
    def getGenesisAccount(self):
        r = requests.get(
            self.__buildRpc("getGenesisAccount")
        )
        return r.json()
    
    def getAccount(self, address):
        r = requests.get(
            self.__buildRpc("getAccount",{"address": address})    
        )
        return r.json()
    
    def getAccountMetaData(self, address):
        r = requests.get(
            self.__buildRpc("getAccountMetaData",{"address": address})    
        )
        return r.json()
    
    def getTransactionHistory(self, txhash=None, ledger_seq=0):
        require(txhash or ledger_seq, "txhash and ledger_seq cant be null at the same time")
        params = {}
        if txhash: params.update({'hash': txhash})
        if ledger_seq: params.update({'ledger_seq': ledger_seq})
        r = requests.get(
            self.__buildRpc("getTransactionHistory",params)    
        )
        return r.json()
    
    def getTransactionCache(self, txhash=None, limit=0):
        require(txhash or limit, "txhash and limit cant be null at the same time")
        params = {}
        if txhash: params.update({'hash': txhash})
        if limit: params.update({'limit': limit})
        r = requests.get(
            self.__buildRpc("getTransactionCache",params)    
        )
        return r.json()

    def getLedger(self, seq, with_validator=False, with_consvalue=False, with_fee=False):
        with_validator = "false" if not with_validator else "true"
        with_consvalue = "false" if not with_consvalue else "true"
        with_fee = "false" if not with_fee else "true"
        r = requests.get(
            self.__buildRpc("getLedger",{"seq": seq, "with_validator": with_validator, "with_consvalue": with_consvalue, "with_fee": with_fee})
        )
        return r.json()

    def getNextNonce(self, address):
        # 不能直接从账户信息中获取nonce，因为可能存在未处理完的交易，从而出现nonce值非递增的情况
        # 另外一种实现方式是sdk中保存nonce值，每次使用的时候依旧要去查询账户信息，如果账户的nonce值小于等于sdk中的nonce值，就说明sdk的nonce值可用，否则，就要更新sdk的nonce值
        limit = 2
        cnt = 0
        while True:
            txcache = self.getTransactionCache(limit=limit)
            # require(txcache['error_code'] == 0)
            if txcache['error_code'] == 4:
                accountinfo = self.getAccount(address)
                nextNonce = int(accountinfo['result'].get("nonce", 0)) + 1
                return nextNonce
            result = txcache['result']
            if result["total_count"] >= limit:
                limit **= 2
            else:
                for tx in result['transactions']:
                    if tx.get('source_address', None) == address:
                        cnt += 1
            time.sleep(1)
        accountinfo = self.getAccount(address)
        nextNonce = int(accountinfo['result'].get("nonce", 0)) + cnt + 1

        return nextNonce

    # 操作类交易

    def __buildTransaction(self, source_address, fee_limit, gas_price, ceil_ledger_seq=0, metadata="", operations=None):
        require(isinstance(operations, dict), "operations must be dict")
        tx = {
            "source_address":source_address,
            "nonce":self.getNextNonce(source_address), 
            "fee_limit": fee_limit, 
            "gas_price": gas_price, 
            "ceil_ledger_seq": ceil_ledger_seq, 
            "metadata": metadata, 
            "operations":[
                {
                    "source_address": source_address,
                    "metadata": metadata,
                }
            ]
        }
        return tx

    def __getPrivateKeyFromAccountDB(self, account):
        return self.accountDB[account]['private_key']

    def sendTx(self, transaction_blob, sign_data, public_key):
        data = {
            "items" : [{
                "transaction_blob" : transaction_blob,
                "signatures" : [{
                    "sign_data" : sign_data,
                    "public_key" : public_key
                }]
            }]
        }
        r = requests.post(
            url=self.__buildRpc("submitTransaction"),
            data=json.dumps(data)
        )
        return r.json()

    def sendTransaction(self, transaction):
        txhash, blob = self.buildBlobFromSource(transaction)
        privateKey = self.__getPrivateKeyFromAccountDB(transaction['source_address'])
        signiture, public_key = self.signTran(transaction_blob=blob, private_key=privateKey)
        result = self.sendTx(blob, signiture, public_key)
        return txhash, result
    
    def waitForTransaction(self, transaction, timeout=30, wait=True):
        txhash, txresult = self.sendTransaction(transaction)
        
        if not wait: return txhash, txresult, ''
        # 查询超时机制
        starttime = time.time()
        resultHistory = self.getTransactionHistory(txhash=txhash)
        while resultHistory['error_code'] != 0:
            require(time.time()-starttime < timeout, "tx timeout(30s), resultHistory: {}".format(resultHistory))
            time.sleep(5)
            resultHistory = self.getTransactionHistory(txhash=txhash)
            continue

        return txhash, txresult, resultHistory


    def create_account_user(self, source_address, dest_address, init_balance=10000000, master_weight=1, tx_threshold=1, metadata="", fee_limit=1000000, gas_price=1000):
        operation = {
            "type": 1,
            "create_account":{
                'dest_address': dest_address,
                "init_balance": init_balance,
                "priv": {
                    "master_weight": master_weight,
                    "thresholds": {
                        "tx_threshold": tx_threshold
                    }
                }
            }
        }
        item = {
            "items": [
                {
                    "transaction_json": {}
                }
            ]
        }
        tx = self.__buildTransaction(source_address=source_address,fee_limit=fee_limit,gas_price=gas_price,metadata=metadata,operations=operation)
        tx['operations'][0].update(operation)

        item['items'][0]['transaction_json'] = tx
        tx['fee_limit'] = self.estimateFee(item)
        # print(tx)
        return self.waitForTransaction(tx)
    
    def create_account_contract(self, source_address, contract_payload, init_input="", init_balance=10000000, master_weight=0, tx_threshold=1, metadata="", fee_limit=1000000, gas_price=1000):
        operation = {
            "type": 1,
            "create_account":{
                "contract": {
                    "payload": contract_payload,
                },
                "init_input": init_input,
                "init_balance": init_balance,
                "priv": {
                    "master_weight": master_weight,
                    "thresholds": {
                        "tx_threshold": tx_threshold
                    }
                }
            }
        }
        item = {
            "items": [
                {
                    "transaction_json": {}
                }
            ]
        }
        tx = self.__buildTransaction(source_address=source_address,fee_limit=fee_limit,gas_price=gas_price,metadata=metadata,operations=operation)
        tx['operations'][0].update(operation)
        item['items'][0]['transaction_json'] = tx
        tx['fee_limit'] = self.estimateFee(item)
        return self.waitForTransaction(tx)
        
    def payCoin(self, source_address, dest_address, amount: int, contract_input: dict, metadata="", fee_limit=1000000, gas_price=1000, wait=True):
        operation = {
            "type": 7,
            "pay_coin": {
                "dest_address": dest_address,
                "amount": amount,
                "input": json.dumps(contract_input)
            }
        }
        item = {
            "items": [
                {
                    "transaction_json": {}
                }
            ]
        }
        tx = self.__buildTransaction(source_address=source_address,fee_limit=fee_limit,gas_price=gas_price,metadata=metadata,operations=operation)
        tx['operations'][0].update(operation)
        item['items'][0]['transaction_json'] = tx
        tx['fee_limit'] = self.estimateFee(item)
        return self.waitForTransaction(tx, wait=wait)
    
    def contract_transact(self, source_address, dest_address, amount: int, contract_input: dict, metadata="", fee_limit=1000000, gas_price=1000):
        return self.payCoin(source_address, dest_address, amount, contract_input, metadata, fee_limit, gas_price)

    def query_contract(self, contract_addr, input ={}, code ="", contract_balance=0, fee_limit=100000000000000000, gas_price=1000, opt_type=2, source_address=""):
        data = {
                    "contract_address" : contract_addr,#可选，智能合约地址
                    "code" : code,#可选，智能合约代码
                    "input" : json.dumps(input),#可选，给被调用的合约传参
                    "contract_balance" : str(contract_balance),#赋予合约的初始 BU 余额
                    "fee_limit" : fee_limit,#手续费
                    "gas_price": gas_price,#可选，gas的价格
                    "opt_type" : opt_type,#可选，操作类型
                    "source_address" : source_address #可选，模拟调用合约的原地址
                }
        r = requests.post(
            url=self.__buildRpc("callContract"),
            data=json.dumps(data)
        )
        return r.json()