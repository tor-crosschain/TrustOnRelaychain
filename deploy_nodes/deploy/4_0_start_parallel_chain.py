import os, sys
sys.path.insert(0, os.path.abspath('.'))
import setting
import argparse
from tools.helper.config_client_helper import ConfigClient
from deploy_nodes.deploy.scripttools import tool_selector

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_name", type=str, default='parallel_chain')
    flag_parser = parser.add_mutually_exclusive_group(required=False)
    flag_parser.add_argument('--reset', dest='reset', action='store_true')
    flag_parser.add_argument('--no-reset', dest='reset', action='store_false')
    parser.set_defaults(reset=False)
    return parser.parse_args()

def main():
    args = getArgs()
    config_name = args.config_name
    config_client = ConfigClient(config_name=config_name, host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    chains= config_client.get()
    for idx, chain_config in enumerate(chains):
        if not args.reset:
            if chain_config['server_nodes'][0].get('rpcport', None) is not None: 
                continue

        chain_type = chain_config['chain_type']
        scripttool = tool_selector.selector(chain_type)

        chain_config = scripttool.pre_start(chain_config)
        chain_config = scripttool.start_chain(chain_config)
        chain_config = scripttool.start_mining(chain_config)
        print("parallel_chain start ok! chain_name: {}".format(chain_config['chain_name']))
        config_client.additem(key_chain=[idx], value=chain_config)
        
    print("finished !!!")

if __name__ == "__main__":
    main()
    
    