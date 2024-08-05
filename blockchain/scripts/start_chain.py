import os, sys
sys.path.insert(0, os.path.abspath('.'))
import json
import setting
from chain.eth_poa import starter as ethpoaStarter
from chain.eth_pow import starter as ethpowStarter

if False:
    from blockchain.scripts.chain.eth_poa import starter as ethpoaStarter
    from blockchain.scripts.chain.eth_pow import starter as ethpowStarter


if __name__ == "__main__":
    chain_type = sys.argv[1]
    chain_id = sys.argv[2]
    chain_config = json.loads(sys.argv[3])
    chain_starter = None
    if chain_type == setting.CHAINTYPE_POA:
        chain_starter = ethpoaStarter
    elif chain_type == setting.CHAINTYPE_POW:
        chain_starter = ethpowStarter
    else:
        raise Exception("unknown chain type: {}".format(chain_type))
    rpcport = chain_starter.start(chain_id, chain_config)
    print(rpcport) # 必须要有这一条语句，远程执行该脚本的时候通过print输出流获取到out
