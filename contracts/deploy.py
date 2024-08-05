import os, sys
import hashlib
sys.path.insert(0, os.path.abspath('.'))

import rlp
from web3.types import MerkleProof

os.environ["SOLC_BINARY"] = "blockchain/bin/solc_0.8.2"

import threading
import setting
import json
import argparse
from typing import List
from tools.sdk.ethsdk import EthSdk
from tools.helper.config_client_helper import ConfigClient

TEST = False

contract_spv_file = "contracts/spv/StateSpv.sol"
# contract_app_file = "spv_ethpow_on_ethpow/contracts/spv/App.sol"

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_name", type=str, default='parallel_chain')
    return parser.parse_args()

def deploy_on_each_chain(chains: List[dict], idx: int, node: dict):
    host, rpcport = node['host'], node['rpcport']
    url = f"http://{host}:{rpcport}"
    ethsdk = EthSdk(url=url, unlock_genesis=False, poa=True)
    address_spv, abi_spv  = ethsdk.compileAndDeploy(contractfile=contract_spv_file, contract_name="StateSpv")
    chains[idx]['contract_address'] = address_spv
    chains[idx]['contract_abi'] = json.dumps(abi_spv)

    if TEST:
        blockHeight = ethsdk.w3.eth.blockNumber
        block = ethsdk.w3.eth.getBlock(blockHeight)
        print(block)
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
            # block['extraData'], # poa 链没有 extraData
            block['mixHash'],
            block["nonce"],
        ])

        receipt, _ = ethsdk.contract_transact(
            contract_address=address_spv,
            contract_abi=abi_spv,
            exec_func="SubmitHeader",
            func_args=[headerRlp]
        )

        assert receipt.status == 1
        print(receipt)

        result = ethsdk.contract_call(contract_address=address_spv, contract_abi=abi_spv, exec_func="GetBlockHeader", func_args=[blockHeight])
        print(result)
    

def deploy():
    args = getArgs()
    config_name = args.config_name
    config_client = ConfigClient(config_name=config_name, host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    chains = config_client.get()
    threads: List[threading.Thread] = []

    for idx, chain_config in enumerate(chains):
        thread = threading.Thread(target=deploy_on_each_chain, args=(chains, idx, chain_config['server_nodes'][0],))
        threads.append(thread)

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    for idx, chain_config in enumerate(chains):
        config_client.additem(key_chain=[idx], value=chain_config)
    

if __name__ == "__main__":
    deploy()
        




# url = "http://10.156.168.198:7545"

# ethsdk = EthSdk(url=url, unlock_genesis=False)

# address_spv, abi_spv  = ethsdk.compileAndDeploy(contractfile=contract_spv_file, contract_name="StateSpv", fromcache=False)



# address_app, abi_app = ethsdk.compileAndDeploy(contractfile=contract_app_file, contract_name="App")
# for i in range(5):
#     key = hashlib.sha256((f"key:{i}").encode()).digest()
#     value = hashlib.sha256(("I am Value"+str(i)).encode()).digest()
#     receipt, _ = ethsdk.contract_transact(contract_address=address_app, contract_abi=abi_app, exec_func="setMessage", func_args=[key, value])
#     assert receipt.status == 1
# # print(receipt)

# position = ethsdk.contract_call(contract_address=address_app, contract_abi=abi_app, exec_func="getPostion", func_args=[key])
# print(f"position: {position}")

# blockHeight = ethsdk.w3.eth.block_number

# proof: MerkleProof = ethsdk.w3.eth.get_proof(address_app, [position], blockHeight)
# print(blockHeight)
# print(proof["accountProof"])
# print(address_app)
# print(proof["address"])
# print(proof["balance"])
# print(proof["codeHash"])
# print(proof["nonce"])
# print(proof["storageHash"])
# print(proof["storageProof"])

# from web3 import Web3
# from eth_abi import encode as abiEncode
# storageValue = ethsdk.w3.eth.get_storage_at(account=address_app, position=position, block_identifier=blockHeight)
# # valueEncoded = Web3.solidity_keccak(abiEncode(types=["string"], args=[value]))
# # valueEncoded = Web3.solidity_keccak(abi_types=["string"], values=[value])
# valueEncoded = abiEncode(types=["bytes"], args=[value])
# print("==============================================")
# print(storageValue)
# print(proof["storageProof"][0]['value'])
# print(proof["storageHash"])
# print(valueEncoded)
# print(value)


# block = ethsdk.w3.eth.get_block(blockHeight)

# headerRlp = rlp.encode([
#     block["parentHash"],
#     block["sha3Uncles"],
#     block["miner"],
#     block["stateRoot"],
#     block["transactionsRoot"],
#     block["receiptsRoot"],
#     block["logsBloom"],
#     block["difficulty"],
#     block["number"],
#     block['gasLimit'],
#     block['gasUsed'],
#     block['timestamp'],
#     block['extraData'],
#     block['mixHash'],
#     block["nonce"],
# ])

# receipt, _ = ethsdk.contract_transact(
#     contract_address=address_spv,
#     contract_abi=abi_spv,
#     exec_func="SubmitHeader",
#     func_args=[headerRlp]
# )

# assert receipt.status == 1
# print(receipt)

# result = ethsdk.contract_call(contract_address=address_spv, contract_abi=abi_spv, exec_func="GetBlockHeader", func_args=[blockHeight])
# print(result)

# def format_proof_nodes(proof):
#     trie_proof = []
#     for rlp_node in proof:
#         trie_proof.append(rlp.decode(bytes(rlp_node)))
#     return trie_proof

# accountProofRlpEncode = rlp.encode([format_proof_nodes(proof["accountProof"])])
# storageProofRlpEncode = rlp.encode([format_proof_nodes(proof["storageProof"][0]['proof'])])
# # bytes32 position, address addr, bytes memory data, uint256 height, bytes memory accountRlpProof,bytes memory storageRlpProof
# flag, err, valint = ethsdk.contract_call(
#     contract_address=address_spv, 
#     contract_abi=abi_spv, 
#     exec_func="verify", 
#     func_args=[
#         position, 
#         address_app, 
#         value, 
#         blockHeight, 
#         accountProofRlpEncode, 
#         storageProofRlpEncode
#     ]
# )   
# print("==============================================")
# print(flag, err, valint)