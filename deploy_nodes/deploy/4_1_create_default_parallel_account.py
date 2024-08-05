import os, sys
import threading
sys.path.insert(0, os.path.abspath('.'))
import time
import json
import shutil
import traceback
import hashlib
import setting

from tools.helper.utils_helper import get_remote_client, create_account_on_eth, create_account_on_bu, auth_new_hit_account
from tools.helper.config_client_helper import ConfigClient
from tools.sdk.ethsdk import EthSdk
from tools.sdk.busdk import BuSdk
from deploy_nodes.deploy.scripttools import tool_selector

def auth_account(nodes, new_account):
    print("准备授权账户: {}".format(new_account))
    for idx, node in enumerate(nodes):
        print("签名者({})正在授权......".format(node['signer_account']['address']))
        rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        ethsdk = EthSdk(rpc, poa=True, unlock_genesis=False)
        auth_new_hit_account(ethsdk, new_account, node['signer_account'])
        print("success !!!")
    print("账户({})已经被授权".format(new_account))

def transfer_account(master_node, poa, account):
    print("创世账户给账户转账......")
    rpc = 'http://{}:{}'.format(master_node['host'], master_node['rpcport'])
    ethSdk = EthSdk(rpc, poa=poa, unlock_genesis=True)
    receipt = ethSdk.sendSingleTransaction(addr_from=ethSdk.genesisAccount, addr_to=account, value=ethSdk.toWei(1000))
    if receipt['status'] == 0: 
        print("transfer failed !")
        return
    print("转账成功")

def getArgs():
    import argparse
    parser = argparse.ArgumentParser()
    flag_parser = parser.add_mutually_exclusive_group(required=False)
    flag_parser.add_argument('--reset', dest='reset', action='store_true')
    flag_parser.add_argument('--no-reset', dest='reset', action='store_false')
    parser.set_defaults(reset=False)
    return parser.parse_args()

def create(chain_config, idx, result):
    scripttool = tool_selector.selector(chain_config['chain_type'])
    pchain_config = scripttool.create_default_account(chain_config)
    result[idx] = pchain_config

def main():
    args = getArgs()
    config_client = ConfigClient(config_name='parallel_chain', host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    chain_config = config_client.get()
    result = {}
    threads = []
    for idx, pchain in enumerate(chain_config):
        print("正在处理平行链{}......".format(pchain['chain_name']))
        threads.append(threading.Thread(
            target=create,
            args=(pchain, idx, result)
        ))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    for idx, chain in result.items():
        config_client.additem(key_chain=[idx], value=chain)
        # for idx_node, node in enumerate(server_nodes):
        #     if not args.reset:
        #         if node.get('default_account', None) is not None: 
        #             continue
        #     if pchain['chain_type'] in ['eth', 'eth-pow', 'eth-hit']:
        #         rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        #         password = hashlib.sha256(str(int(time.time()*1000)).encode('utf-8')).hexdigest()
        #         ishit = pchain['chain_type'] == 'eth-hit'
        #         ethsdk = EthSdk(rpc, poa=ishit)
        #         account_address = create_account_on_eth(ethSdk=ethsdk,password=password)
        #         if ishit: auth_account(server_nodes, new_account=account_address)
        #         transfer_account(server_nodes[0], ishit, account_address)
        #         account = {
        #             'address': account_address,
        #             'password': password
        #         }
        #     elif pchain['chain_type'] in ['bu']:
        #         rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        #         password = ''
        #         genesis_account = pchain['genesis_account']
        #         busdk = BuSdk(rpc,genesisAccountInfo={genesis_account['address']: genesis_account})
        #         print(busdk.genesisAccount)
        #         print(busdk.accountDB)
        #         account = create_account_on_bu(busdk)
        #         account.update({'password': password})
        #     else:
        #         raise Exception("unknown chain-type")
                
    print("finished !!!")

if __name__ == "__main__":
    main()
    
    