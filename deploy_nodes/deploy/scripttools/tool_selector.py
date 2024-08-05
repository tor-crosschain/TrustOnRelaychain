import os, sys
sys.path.insert(0, os.path.abspath('.'))
import setting
from deploy_nodes.deploy.scripttools.bu.tool import Tool as ScriptToolBu
from deploy_nodes.deploy.scripttools.eth_poa.tool import Tool as ScriptToolEthPoa
from deploy_nodes.deploy.scripttools.eth_pow.tool import Tool as ScriptToolEthPow
from deploy_nodes.deploy.scripttools.eth_hit.tool import Tool as ScriptToolHit

def selector(chain_type):
    scripttool = None
    if chain_type == setting.CHAINTYPE_POW:
        scripttool = ScriptToolEthPow()
    elif chain_type == setting.CHAINTYPE_POA:
        scripttool = ScriptToolEthPoa()
    elif chain_type == setting.CHAINTYPE_BU:
        scripttool = ScriptToolBu()
    elif chain_type == setting.CHAINTYPE_HIT:
        scripttool = ScriptToolHit()
    else:
        raise Exception("invalid chain type: {}".format(chain_type))
    return scripttool