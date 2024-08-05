from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath("."))
import argparse
import time
import setting
import multiprocessing
from loguru import logger
from eth_account import Account
from typing import List, Dict
from tools.helper.config_client_helper import ConfigClient
from tools.helper.utils_helper import exec_command_local
from tools.sdk.ethsdk import EthSdk

def create_configs(paranum: int):
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT, config_name='server')
    servers = config_client.get()

    chain_configs = []
    # add relay chain
    server = servers[0]
    chain_configs.append({
        "chain_name": f"relay_chain_{0}",
        "chain_type": "eth-poa",
        "bootnode": {
            "host": server['host'],
            "port": server['port'],
            "username": server['username'],
            "password": server['password'],
            "bootnode_key": f"relay_chain_{0}_bootnode"
        },
        "server_nodes": [
            {
                "host": server['host'],
                "port": server['port'],
                "username": server['username'],
                "password": server['password'],
            }
        ]
    })
    # add parachains
    for i in range(paranum):
        index = i % len(servers)
        server = servers[index]
        chain_config = {
            "chain_name": f"parallel_chain_{i+1}", # relay chain is 0
            "chain_type": "eth-poa",
            "bootnode": {
                "host": server['host'],
                "port": server['port'],
                "username": server['username'],
                "password": server['password'],
                "bootnode_key": f"parallel_chain_{i+1}_bootnode"
            },
            "server_nodes": [
                {
                    "host": server['host'],
                    "port": server['port'],
                    "username": server['username'],
                    "password": server['password'],
                }
            ]
        }
        chain_configs.append(chain_config)
    
    config_name = f'blockchains_tor_{paranum}'
    config_client.create(config=chain_configs, config_name=config_name)
    return config_name

def main():
    args = get_args()
    paranum = int(args.paranum)
    config_name = create_configs(paranum)
    print(config_name)
    
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paranum", type=int, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    main()