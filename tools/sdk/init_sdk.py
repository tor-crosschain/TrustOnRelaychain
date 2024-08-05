from tools.sdk.busdk import BuSdk
from tools.sdk.ethsdk import EthSdk
from tools.sdk import types

def create_sdk(chain_type:str, rpc_addr: str, **kwargs):
    if chain_type in [types.ETH, types.ETHPOW]:
        return EthSdk(rpc_addr, unlock_genesis=False, **kwargs)
    if chain_type in [types.ETHPOA, types.HIT]:
        return EthSdk(rpc_addr,poa=True, unlock_genesis=False, **kwargs)
    if chain_type == types.BU:
        return BuSdk(rpc_addr)
    if chain_type == types.FABRIC:
        return None
    return None
    