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
from tools.helper.config_client_helper import ConfigClient
from tools.sdk.ethsdk import EthSdk
from web3.types import BlockData, MerkleProof
from eth_account import Account

TEST_INIT_ACCOUNT = False
TEST_SEND_CM = False

def format_proof_nodes(proof):
    trie_proof = []
    for rlp_node in proof:
        trie_proof.append(rlp.decode(bytes(rlp_node)))
    return trie_proof

class GatewayFromRelayToPara:
    def __init__(self, chain_id: int, chain_url: str, dst_chain_id: int, dst_chain_url: str, ) -> None:
        self.chain_id = chain_id
        assert self.chain_id == 0 # the src must be relay chain
        self.chain_url = chain_url
        self.ethsdk = EthSdk(url=chain_url, poa=True, unlock_genesis=False)
        self.dst_chain_id = dst_chain_id
        self.dst_chain_url = dst_chain_url
        self.dst_ethsdk = EthSdk(url=dst_chain_url, poa=True, unlock_genesis=False)
        self.__header_queue = queue.Queue()
        self.__txhash_queue = queue.Queue()
    
    def set_contract(self, address: str, abi: dict) -> GatewayFromRelayToPara:
        self.address = address
        self.abi = abi
        return self
    
    def set_dst_contract(self, address: str, abi: dict) -> GatewayFromRelayToPara:
        self.dst_address = address
        self.dst_abi = abi
        return self
    
    def set_header_account(self, privatekey: str) ->GatewayFromRelayToPara:
        account = Account.from_key(privatekey)
        self.header_address = account.address
        self.header_privatekey = account.key
        return self
    
    def set_tx_account(self, privatekey: str) ->GatewayFromRelayToPara:
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
            self.send_header(block)
    
    def send_header(self, block: BlockData):
        headerRlp = rlp.encode([
            block["parentHash"],
            block["sha3Uncles"],
            block["miner"],
            block["stateRoot"],
            block["transactionsRoot"],
            block["receiptsRoot"],
            block["logsBloom"],
            block["difficulty"],
            block["number"],
            block['gasLimit'],
            block['gasUsed'],
            block['timestamp'],
            block['mixHash'],
            block["nonce"],
        ])

        receipt, _ = self.dst_ethsdk.sendrawTransaction(
            contract_address=self.dst_address,
            contract_abi=self.dst_abi,
            exec_func="SubmitHeader",
            func_args=[self.chain_id, headerRlp],
            source_args={'from': self.header_address, 'privatekey': self.header_privatekey}
        )

        assert receipt.status == 1, f"txhash: {receipt['transactionHash'].hex()}"
        print(f"submit block({block['number']}) of chain-{self.chain_id} to chain-{self.dst_chain_id} ok!")

def main():
    args = get_args()
    tag = args.tag
    config_name = args.config_name
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT, config_name=config_name)
    chains = config_client.get()
    srcid, dstid = args.srcid, args.dstid
    srcChain = chains[srcid]
    dstChain = chains[dstid]
    src_chain_url = f"http://{srcChain['server_nodes'][0]['host']}:{srcChain['server_nodes'][0]['rpcport']}"
    dst_chain_url = f"http://{dstChain['server_nodes'][0]['host']}:{dstChain['server_nodes'][0]['rpcport']}"
    gateway = GatewayFromRelayToPara(chain_id=srcid, chain_url=src_chain_url, dst_chain_id=dstid, dst_chain_url=dst_chain_url)
    gateway.set_contract(address=srcChain['contract_address'], abi=json.loads(srcChain['contract_abi'])).\
    set_dst_contract(address=dstChain['contract_address'], abi=json.loads(dstChain['contract_abi'])).\
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

    thread_listen.start()
    thread_deal.start()

    if TEST_SEND_CM:
        # send cross-chain tx to src chain
        txhashes = []
        for i in range(20):
            txhash, _ = gateway.ethsdk.contract_transact(
                contract_address=gateway.address,
                contract_abi=gateway.abi,
                exec_func='crossSend',
                func_args=[
                    0, 1, gateway.dst_address, gateway.dst_address, b'targetFunc', ('targetData'+str(i)).encode()
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