import os, sys
sys.path.insert(0, os.path.abspath('.'))
import json
import setting
from chain.eth_poa import prestarter as ethpoaPreStarter
from chain.eth_pow import prestarter as ethpowPreStarter

if False:
    from blockchain.scripts.chain.eth_poa import prestarter as ethpoaPreStarter
    from blockchain.scripts.chain.eth_pow import prestarter as ethpowPreStarter
    from blockchain.scripts.chain.hit import prestarter as hitPreStarter
    from blockchain.scripts.chain.bu import prestarter as buPreStarter


if __name__ == "__main__":
    chain_type = sys.argv[1]
    chain_id = sys.argv[2]
    chain_config = json.loads(sys.argv[3])
    chain_prestarter = None
    if chain_type == setting.CHAINTYPE_POA:
        chain_prestarter = ethpoaPreStarter
    elif chain_type == setting.CHAINTYPE_POW:
        chain_prestarter = ethpowPreStarter
    else:
        raise Exception("unknown chain type: {}".format(chain_type))
    return_value = chain_prestarter.prestart(chain_id, chain_config)
    print(return_value) # 必须要有这一条语句，远程执行该脚本的时候通过print输出流获取到out
