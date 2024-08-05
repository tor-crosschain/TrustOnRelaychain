import sys, os
sys.path.insert(0, os.path.abspath('.'))

import setting
import argparse
from tools.helper.utils_helper import exec_command_remote
from tools.helper.remote_helper import Remote
from tools.helper.config_client_helper import ConfigClient

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_name", type=str, default='parallel_chain')
    return parser.parse_args()

def main():
    args = getArgs()
    config_name = args.config_name
    config_client = ConfigClient(config_name=config_name, host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    chains = config_client.get()
    for idx, chain_config in enumerate(chains):
        for node in chain_config['server_nodes']:
            host, port, rpcport = node['host'], node['port'], node['rpcport']
            username, password = node['username'], node['password']
            print(f"work with {host}:{port}, rpcport: {rpcport}")
            remote = Remote(host=host, username=username, password=password, port=port)
            cmd = f"pkill -f 'rpcport {rpcport}'"
            try:
                exec_command_remote(remote=remote, cmd=cmd)
            except Exception as e:
                print(f"stop geth({rpcport}) on {host}:{port} failed, err: {e}")

if __name__ == "__main__":
    main()