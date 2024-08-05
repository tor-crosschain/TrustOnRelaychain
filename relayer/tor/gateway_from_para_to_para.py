from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath("."))
import argparse
import json
import time
import queue
import rlp
import setting
import threading
import hashlib
import math
import multiprocessing
from typing import List, Tuple
from tools.helper.config_client_helper import ConfigClient
from tools.sdk.ethsdk import EthSdk
from web3.types import BlockData, MerkleProof
from eth_account import Account
from tools.helper.merkle_helper import MerkleBinaryTree

TEST_INIT_ACCOUNT = False
TEST_SEND_CM = False

def format_proof_nodes(proof):
    trie_proof = []
    for rlp_node in proof:
        trie_proof.append(rlp.decode(bytes(rlp_node)))
    return trie_proof

class Info:
    def __init__(self, key, value) -> None:
        self.key = key
        self.value = value
    
    def as_json(self) -> dict:
        return {
            self.key: self.value
        }

class GatewayFromParaToPara:
    def __init__(self, chain_id: int, chain_url: str, dst_chain_id: int, dst_chain_url: str, relay_chain_id: int, relay_chain_url: str, info_queue: multiprocessing.Queue = None) -> None:
        self.chain_id = chain_id
        self.chain_url = chain_url
        self.ethsdk = EthSdk(url=chain_url, poa=True, unlock_genesis=False)
        self.dst_chain_id = dst_chain_id
        self.dst_chain_url = dst_chain_url
        self.dst_ethsdk = EthSdk(url=dst_chain_url, poa=True, unlock_genesis=False)
        assert relay_chain_id == 0
        self.relay_chain_id = relay_chain_id
        self.relay_chain_url = relay_chain_url
        self.relay_ethsdk = EthSdk(url=relay_chain_url, poa=True, unlock_genesis=False)
        self.__header_queue = queue.Queue()
        self.__txhash_queue = queue.Queue()
        self.__info_queue = info_queue
    
    def collect_info(self, info: Info):
        if self.__info_queue is None:
            return
        self.__info_queue.put(info)
    
    def set_contract(self, address: str, abi: dict) -> GatewayFromParaToPara:
        self.address = address
        self.abi = abi
        return self
    
    def set_dst_contract(self, address: str, abi: dict) -> GatewayFromParaToPara:
        self.dst_address = address
        self.dst_abi = abi
        return self
    
    def set_relay_contract(self, address: str, abi: dict) -> GatewayFromParaToPara:
        self.relay_address = address
        self.relay_abi = abi
        return self
    
    def set_header_account(self, privatekey: str) ->GatewayFromParaToPara:
        account = Account.from_key(privatekey)
        self.header_address = account.address
        self.header_privatekey = account.key
        return self
    
    def set_tx_account(self, privatekey: str) ->GatewayFromParaToPara:
        account = Account.from_key(privatekey)
        self.tx_address = account.address
        self.tx_privatekey = account.key
        self.tx_nonce = self.dst_ethsdk.w3.eth.get_transaction_count(self.tx_address)
        return self
    
    def query_block(self):
        now_height = self.ethsdk.w3.eth.block_number
        walk_height = now_height
        while True:
            if walk_height > now_height:
                now_height = self.ethsdk.w3.eth.block_number
                time.sleep(1)
                continue
            block = self.ethsdk.w3.eth.get_block(walk_height)
            print(f"get block: {walk_height}")
            walk_height += 1
            self.__header_queue.put(block)
    
    def deal_block(self):
        while True:
            block: BlockData = self.__header_queue.get()
            # self.send_header(block)
            self.deal_txs(block['transactions'])
    
    def deal_txs(self, txhashes):
        cmIndexes = []
        height =  0
        for txhash in txhashes:
            # check transaction receipt
            receipt = self.ethsdk.w3.eth.get_transaction_receipt(txhash)
            if receipt['to'] != self.ethsdk.w3.to_checksum_address(self.address):
                print(f"to not match: {receipt['to']},  {self.ethsdk.w3.to_checksum_address(self.address)}")
                continue
            if receipt["status"] != 1:
                print(f"receipt status != 1, hash: {receipt['transactionHash'].hex()}")
                continue
            # check input of transaction
            transaction = self.ethsdk.w3.eth.get_transaction(txhash)
            contract = self.ethsdk.w3.eth.contract(abi=self.abi)
            decoded_input = contract.decode_function_input(transaction["input"])
            func, params = decoded_input[0], decoded_input[1]
            print(func)
            print(params)
            infokey = f"{self.chain_id}-{func.fn_name}-{txhash.hex()}"
            self.collect_info(Info(key=infokey, value=receipt['gasUsed']))            
            if not str(func.fn_name).startswith("crossSend"):
                print(f"funcname is {func.fn_name}")
                continue
            # # build merkle tree for all cross-chain messages in this block
            # if params["targetChain"] != self.dst_chain_id:
            #     print(f"params['targetChain'] is {params['targetChain']}, not {self.dst_chain_id}")
            #     continue
            # parse event
            events = self.ethsdk.parseEvent(contract, receipt, event_names=['CMIndex'])
            print(events)
            cmIndex = events['CMIndex'][0]['index']
            print(f"obtain cross-chain message index on source parachain: {cmIndex}")
            cmIndexes.append(cmIndex)
            # self.query_construct_dst_tx(receipt["blockNumber"], cmIndex)
            if height == 0: height = receipt['blockNumber']
        
        if len(cmIndexes) == 0:
            return

        bcr = self.query_bcr(height)
        
        cmHashes, proofs = self.construct_proof_first_layer(cmIndexes, bcr)

        self.deal_bcr(bcr, height)

        self.send_cm(height, cmIndexes, cmHashes, proofs)

    def deal_bcr(self, bcr: bytes, source_height: int):
        print("waiting bcr proof ...")
        while True:
            bcr = self.relay_ethsdk.contract_call(
                contract_address=self.relay_address,
                contract_abi=self.relay_abi,
                exec_func='getBCR',
                func_args=[self.chain_id, source_height]
            )
            if bcr != bytes(32):
                print(f"obtain bcr on the relay chain! chain_id: {self.chain_id}, source_height: {source_height}, bcr: {bcr.hex()}")
                break
            time.sleep(1)

        # query confirmed block height on the realy chain
        relay_height = self.relay_ethsdk.contract_call(
            contract_address=self.relay_address,
            contract_abi=self.relay_abi,
            exec_func='getBCRHeightOnRelay',
            func_args=[bcr]
        )
        assert relay_height != 0

        # query state proof of bcr on the relay chain
        position = self.relay_ethsdk.contract_call(
            contract_address=self.relay_address, 
            contract_abi=self.relay_abi, 
            exec_func="getStorageLocationOfBCROnRelay", 
            func_args=[self.chain_id, source_height]
        )
        proof: MerkleProof = self.relay_ethsdk.w3.eth.get_proof(self.relay_address, [position], relay_height)
        accountProofRlpEncode = rlp.encode([format_proof_nodes(proof["accountProof"])])
        storageProofRlpEncode = rlp.encode([format_proof_nodes(proof["storageProof"][0]['proof'])])

        # wait block of relay_height to be confirmed on the dst parachain
        print(f"wait block-{relay_height} of relay chain to be confirmed on the dst parachain-{self.dst_chain_id}")
        while True:
            header = self.dst_ethsdk.contract_call(
                contract_address=self.dst_address,
                contract_abi=self.dst_abi,
                exec_func='GetBlockHeader',
                func_args=[0, relay_height]
            )
            if header[2] == relay_height:
                print(f"block-{relay_height} of relay chain has been confirmed on the dst parachain-{self.dst_chain_id}")
                break
            time.sleep(1)
            

        # send bcr to the dst chain
        txhash, _ = self.dst_ethsdk.sendrawTransaction(
            contract_address=self.dst_address, 
            contract_abi=self.dst_abi, 
            exec_func="crossReceiveBCR", 
            func_args=[
                self.chain_id, 
                source_height,
                bcr, 
                position, 
                self.relay_address,
                relay_height, 
                accountProofRlpEncode, 
                storageProofRlpEncode
            ],
            source_args={
                'from': self.tx_address, 
                'privatekey': self.tx_privatekey,
                'nonce': self.tx_nonce,
                'gas': 2000000
            },
            wait=False
        )
        self.tx_nonce += 1
        self.__txhash_queue.put(('BCR', txhash))
        print(f"submit bcr(confirmed on the relay chain's block-{relay_height}) in block-{source_height} of source parachain-{self.chain_id} to dst parachain-{self.dst_chain_id} ok! txhash: {txhash.hex()}")


    def construct_proof_first_layer(self, cmIndexes: list, bcr: bytes) -> Tuple[List[bytes], List[List[bytes]]]:

        cmHashes = []
        for idx, cmIndex in enumerate(cmIndexes):
            cmHash = self.ethsdk.contract_call(
                contract_address=self.address,
                contract_abi=self.abi,
                exec_func='getCMHashByIndex',
                func_args=[cmIndex]
            )
            cmHashes.append(cmHash)
        
        mbt = MerkleBinaryTree(cmHashes)    
        mbt.build()
        root = mbt.get_root()
        assert root == bcr, f"root({root.hex()}) not equal to BCR({bcr.hex()})"

        proofs: List[List[bytes]] = []
        for i in range(len(cmIndexes)):
            proofs.append(mbt.get_proof(i))
        
        return cmHashes, proofs
        
    
    def query_bcr(self, height) -> bytes:
        bcr = self.ethsdk.contract_call(
            contract_address=self.address,
            contract_abi=self.abi,
            exec_func='retrieveRoot',
            func_args=[height]
        )
        assert bcr != 0x00
        print(f"query bcr in the block-{height} on the source parallel chain-{self.chain_id}! bcr: {bcr.hex()}")
        return bcr

    def send_cm(self, height: int, cmIndexes: List[int], cmHashes: List[bytes], proofs: List[List[bytes]]):
        for idx, cmIndex in enumerate(cmIndexes):
            self.query_construct_dst_tx(height, idx, cmIndex, cmHashes[idx], proofs[idx])


    def query_construct_dst_tx(self, height: int, position: int, cmIndex: int, cmHash: bytes, proof: List[bytes]):
        # get cmHash and cm
        cm = self.ethsdk.contract_call(
            contract_address=self.address,
            contract_abi=self.abi,
            exec_func='getCMByIndex',
            func_args=[cmIndex]
        )

        if cm[1] != self.dst_chain_id:
            print(f"cm(targetChain={cm[1]}) should not be sent to dst parachain-{self.dst_chain_id}")
            return

        txhash, _ = self.dst_ethsdk.sendrawTransaction(
            contract_address=self.dst_address, 
            contract_abi=self.dst_abi, 
            exec_func="crossReceiveFromParaToR", 
            func_args=[
                cm, 
                cmHash, 
                position, 
                height, 
                proof
            ],
            source_args={
                'from': self.tx_address, 
                'privatekey': self.tx_privatekey,
                'nonce': self.tx_nonce,
                'gas': 2000000
            },
            wait=False
        )
        self.tx_nonce += 1
        self.__txhash_queue.put(('cross-chain message', txhash))
        print(f"submit cross-chain message({cmIndex}) in block({height}) of source parachain-{self.chain_id} to dst parachain-{self.dst_chain_id} ok! txhash: {txhash.hex()}")
    
    def deal_txhash(self):
        while True:
            msgtype, txhash = self.__txhash_queue.get()
            receipt = self.dst_ethsdk.waitForTransactionReceipt(txhash)
            status = receipt['status']
            if status != 1:
                transaction = self.dst_ethsdk.w3.eth.get_transaction(txhash)
                contract = self.dst_ethsdk.w3.eth.contract(abi=self.abi)
                decoded_input = contract.decode_function_input(transaction["input"])
                func, params = decoded_input[0], decoded_input[1]
                print(f"{msgtype} transaction on dst-chain-{self.dst_chain_id} fails! func: {func.fn_name}; params: {params}; to: {transaction['to']}; txhash: {txhash.hex()}")
            else:
                print(f"{msgtype} transaction on dst-chain-{self.dst_chain_id}-(height={receipt['blockNumber']}) succeeds! txhash: {txhash.hex()}")

def collect_info(info_queue: multiprocessing.Queue, config_name: str, srcid, dstid, tag):
    info_path = f"info/tor/{config_name}/{tag}/parachain"
    if not os.path.exists(info_path):
        os.makedirs(info_path)
    filename = os.path.join(info_path, f'{srcid}-{dstid}-info.ignore.json')
    
    infos = []
    starttime = time.time()
    while True:
        info: Info = info_queue.get()
        infos.append(info.as_json())
        now = time.time()
        if now-starttime>2: # write to file every 5 seconds
            json.dump(infos, fp=open(filename, 'w'))
        

def main():
    args = get_args()
    tag = args.tag
    config_name = args.config_name
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT, config_name=config_name)
    chains = config_client.get()
    srcid, dstid = args.srcid, args.dstid

    # set collect process
    info_queue = multiprocessing.Manager().Queue()
    collect_proc = multiprocessing.Process(target=collect_info, args=(info_queue, config_name, srcid, dstid, tag))
    collect_proc.start()

    
    srcChain = chains[srcid]
    dstChain = chains[dstid]
    relayChain = chains[0]
    src_chain_url = f"http://{srcChain['server_nodes'][0]['host']}:{srcChain['server_nodes'][0]['rpcport']}"
    dst_chain_url = f"http://{dstChain['server_nodes'][0]['host']}:{dstChain['server_nodes'][0]['rpcport']}"
    relay_chain_url = f"http://{relayChain['server_nodes'][0]['host']}:{relayChain['server_nodes'][0]['rpcport']}"
    gateway = GatewayFromParaToPara(chain_id=srcid, chain_url=src_chain_url, dst_chain_id=dstid, dst_chain_url=dst_chain_url, relay_chain_id=0, relay_chain_url=relay_chain_url, info_queue=info_queue)
    gateway.set_contract(address=srcChain['contract_address'], abi=json.loads(srcChain['contract_abi'])).\
    set_dst_contract(address=dstChain['contract_address'], abi=json.loads(dstChain['contract_abi'])).\
    set_relay_contract(address=relayChain['contract_address'], abi=json.loads(relayChain['contract_abi'])).\
    set_header_account(privatekey=args.header_private_key).\
    set_tx_account(privatekey=args.tx_private_key)

    


    

    # # # #
    if TEST_INIT_ACCOUNT:
        # transfer to header account
        header_key = args.header_private_key
        account = Account.from_key(header_key)
        address = account.address
        receipt = gateway.dst_ethsdk.sendSingleTransaction(
            addr_from=gateway.dst_ethsdk.defaultAccount,
            addr_to=address,
            value=gateway.dst_ethsdk.toWei(1),
        )
        assert receipt["status"] == 1
        print("transfer to header account ok!")

        tx_key = args.tx_private_key
        account = Account.from_key(tx_key)
        address = account.address
        receipt = gateway.dst_ethsdk.sendSingleTransaction(
            addr_from=gateway.dst_ethsdk.defaultAccount,
            addr_to=address,
            value=gateway.dst_ethsdk.toWei(1),
        )
        assert receipt["status"] == 1
        print("transfer to tx account ok!")

    # # # #

    thread_listen = threading.Thread(target=gateway.query_block)
    thread_deal = threading.Thread(target=gateway.deal_block)
    thread_deal_txhash = threading.Thread(target=gateway.deal_txhash)

    thread_listen.start()
    thread_deal.start()
    thread_deal_txhash.start()

    if TEST_SEND_CM:
        # send cross-chain tx to src chain
        txhashes = []
        for i in range(50):
            txhash, _ = gateway.ethsdk.contract_transact(
                contract_address=gateway.address,
                contract_abi=gateway.abi,
                exec_func='crossSendToR',
                func_args=[
                    1, 2, gateway.dst_address, gateway.dst_address, b'targetFunc', ('targetData'+str(i)).encode()
                ],
                wait=False
            )
            txhashes.append(txhash)
            time.sleep(1)
        for txhash in txhashes:
            receipt = gateway.ethsdk.waitForTransactionReceipt(txhash)
            assert receipt['status'] == 1
        print("send cross-chain transaction ok!")

    thread_listen.join()
    thread_deal.join()
    thread_deal_txhash.join()
    collect_proc.join()
    

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--srcid", type=int, required=True)
    parser.add_argument("--dstid", type=int, required=True)
    parser.add_argument("--header_private_key", type=str, required=True)
    parser.add_argument("--tx_private_key", type=str, required=True)
    parser.add_argument("--config_name", type=str, required=True)
    parser.add_argument("--tag", type=str, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    main()