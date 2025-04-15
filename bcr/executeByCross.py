"""
包含了不需要BCR的跨链交易发起方式
"""

from __future__ import annotations
import os, sys
import re
import collections
import setting
import argparse
sys.path.insert(0, os.path.abspath("."))
import subprocess
from tools.sdk.ethsdk import EthSdk
from typing import List
from web3.types import TxReceipt
import math, json
from tools.helper.config_client_helper import ConfigClient

config_name = "parallel_chain"
config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT, config_name=config_name)
chain_configs = config_client.get()
chain = chain_configs[0]
node = chain['server_nodes'][0]

ETH_PORT = int(node['port'])
ETH_HOST = node['host']
ETH_URL = f"http://{ETH_HOST}:{ETH_PORT}"
LEAVESNUM = 1000
OUTPUT_FILE = "./bcr/result/data_{name}.json"
os.environ["SOLC_BINARY"] = "./blockchain/bin/solc_0.8.17"
average = lambda x: sum(x) / len(x)

server_setting = json.load(open("./bcr/setting.json"))

class ContractInfo:
    def __init__(self) -> None:
        self.abi = ""
        self.opcode = 0x00
        self.filepath = ""
        self.name = ""
        self.address = ""
        self.testname = ""

    def set_testname(self, testname: str) -> ContractInfo:
        self.testname = testname
        return self

    def set_address(self, address: str) -> ContractInfo:
        self.address = address
        return self

    def set_name(self, name: str) -> ContractInfo:
        self.name = name
        return self

    def set_filepath(self, filepath: str) -> ContractInfo:
        self.filepath = filepath
        return self

    def set_abi(self, abi: str) -> ContractInfo:
        self.abi = abi
        return self

    def set_opcode(self, opcode: bytes) -> ContractInfo:
        self.opcode = opcode
        return self


class ContractManager:
    Cross: ContractInfo = (
        ContractInfo().set_filepath("./bcr/contracts/Cross.sol").set_name("Cross")
    )
    UpdateNull: ContractInfo = (
        ContractInfo()
        .set_filepath("./bcr/contracts/UpdateNull.sol")
        .set_name("UpdateNull")
    )
    BCRUpdate: ContractInfo = (
        ContractInfo()
        .set_filepath("./bcr/contracts/BCRUpdate.sol")
        .set_name("BCRUpdate")
    )
    BCRUpdateOpt: ContractInfo = (
        ContractInfo()
        .set_filepath("./bcr/contracts/BCRUpdateOpt.sol")
        .set_name("BCRUpdateOpt")
    )
    UpdateByLeaves: ContractInfo = (
        ContractInfo()
        .set_filepath("./bcr/contracts/UpdateByLeaves.sol")
        .set_name("UpdateByLeaves")
    )
    UpdateByTree: ContractInfo = (
        ContractInfo()
        .set_filepath("./bcr/contracts/UpdateByTree.sol")
        .set_name("UpdateByTree")
    )


def get_durs(txhashes: List[str]):
    cmd = """ ssh {}@{} -p {} "{}" """.format(
        server_setting['username'],
        server_setting['ip'],
        server_setting['port'],
        "docker exec tor_cc_env /bin/bash -c \\\"cat /root/workspace/blockchain/parallel_chain/0/start.log | grep 'applyTransaction'\\\""
    )
    with os.popen(cmd) as r:
        pat = re.compile(pattern="dur=(\d+).*txhash=(0x.{64})")
        items = list(
            filter(
                lambda x: str(x[1]).lower() in txhashes,
                map(
                    lambda x: (int(x[0]), str(x[1]).lower()),
                    [pat.findall(log)[0] for log in r.readlines()],
                ),
            ),
        )

    itemsmap = {}
    for dur, txhash in items:
        if txhash not in itemsmap:
            itemsmap[txhash] = []
        itemsmap[txhash].append(dur)

    durs = [average(itemsmap.get(txhash, [0])) for txhash in txhashes]

    return durs


def measure(sdk: EthSdk, cinfo: ContractInfo) -> [float, float]:
    assert cinfo.address, f"address is empty: {cinfo.address}"
    assert cinfo.abi, f"abi is empty: {cinfo.abi}"
    sdk.w3.geth.miner.stop()
    txhashes = [
        sdk.contract_transact(
            contract_address=cinfo.address,
            contract_abi=cinfo.abi,
            exec_func="crossTransfer",
            func_args=[
                10000 + i,
                10000 + i,
                10000 + i,
                10000 + i,
                cinfo.address,
                cinfo.address,
                cinfo.address,
                b"sourceFunc",
                b"targetFunc",
                b"targetData",
                1,
            ],
            source_args={"gas": 10000000},
            wait=False,
        )[0].hex()
        for i in range(LEAVESNUM)
    ]
    sdk.w3.geth.miner.start()
    print("wait crossTransfer receipts...")
    receipts: List[TxReceipt] = [
        sdk.waitForTransactionReceipt(txhash=txhash) for txhash in txhashes
    ]
    status = [int(r["status"]) == 1 for r in receipts]
    assert all(
        status
    ), f"txreceipts failed! fail num: {collections.Counter(status)[False]}"

    # analysis stored hashes
    hashesnum = []
    for i in range(LEAVESNUM):
        hashnum = sdk.contract_call(
            contract_address=cinfo.address,
            contract_abi=cinfo.abi,
            exec_func="queryHashNum",
            func_args=[1, i + 1],
        )
        hashesnum.append(hashnum)

    # analysis gasUsed
    BATCH_SIZE = int(math.sqrt(LEAVESNUM))
    gasUseds = [receipt["gasUsed"] for receipt in receipts]
    gasUseds_batch = [
        average(gasUseds[i : i + BATCH_SIZE])
        for i in range(0, len(gasUseds), BATCH_SIZE)
    ]
    print(f"gasUsed batch: {gasUseds_batch}")
    average_gas = sum(gasUseds) / len(gasUseds)
    print(f"block number: {set(receipt['blockNumber'] for receipt in receipts)}")

    # analysis duration
    durs = get_durs(txhashes=txhashes)
    durs_batch = [
        average(durs[i : i + BATCH_SIZE]) for i in range(0, len(durs), BATCH_SIZE)
    ]
    print(f"durs batch: {durs_batch}")
    print(f"durs length: {len(durs)}")
    # assert len(durs) == len(txhashes), f"durs: {durs}"
    average_dur = sum(durs) / len(durs)

    # write to file
    json.dump(
        obj={
            "gasUseds": gasUseds,
            "hashesNum": hashesnum,
            "durs": durs,
            "average_gas": average_gas,
            "average_dur": average_dur,
        },
        fp=open(OUTPUT_FILE.format(name=cinfo.testname), "w"),
    )
    return average_gas, average_dur


def prepare(ethsdk: EthSdk, alg_case: int):
    address_cross, abi_cross = ethsdk.compileAndDeploy(
        contractfile=ContractManager.Cross.filepath,
        contract_name=ContractManager.Cross.name,
    )
    print(f"address_cross: {address_cross}")

    testname = ""
    if alg_case == 0:
        print("deploy UpdateNull ...")
        address_update, abi_update = ethsdk.compileAndDeploy(
            contractfile=ContractManager.UpdateNull.filepath,
            contract_name=ContractManager.UpdateNull.name,
        )
        ContractManager.UpdateNull.set_address(address_update).set_abi(abi_update)
        testname = "UpdateNull"
    elif alg_case == 1:
        print("deploy BCRUpdate ...")
        address_update, abi_update = ethsdk.compileAndDeploy(
            contractfile=ContractManager.BCRUpdate.filepath,
            contract_name=ContractManager.BCRUpdate.name,
        )
        ContractManager.BCRUpdate.set_address(address_update).set_abi(abi_update)
        testname = "BCRUpdate"
    elif alg_case == 2:
        print("deploy BCRUpdateOpt ...")
        address_update, abi_update = ethsdk.compileAndDeploy(
            contractfile=ContractManager.BCRUpdateOpt.filepath,
            contract_name=ContractManager.BCRUpdateOpt.name,
        )
        ContractManager.BCRUpdateOpt.set_address(address_update).set_abi(abi_update)
        testname = "BCRUpdateOpt"
    elif alg_case == 3:
        print("deploy UpdateByLeaves ...")
        address_update, abi_update = ethsdk.compileAndDeploy(
            contractfile=ContractManager.UpdateByLeaves.filepath,
            contract_name=ContractManager.UpdateByLeaves.name,
        )
        ContractManager.UpdateByLeaves.set_address(address_update).set_abi(abi_update)
        testname = "UpdateByLeaves"
    elif alg_case == 4:
        print("deploy UpdateByTree ...")
        address_update, abi_update = ethsdk.compileAndDeploy(
            contractfile=ContractManager.UpdateByTree.filepath,
            contract_name=ContractManager.UpdateByTree.name,
        )
        ContractManager.UpdateByTree.set_address(address_update).set_abi(abi_update)
        testname = "UpdateByTree"
    else:
        raise Exception(f"unknown alg_case({alg_case})")

    ContractManager.Cross.set_address(address_cross).set_abi(abi_cross).set_testname(
        testname
    )

    print(f"set update Alg: {alg_case}, {address_update}")
    txreceipt, _ = ethsdk.contract_transact(
        contract_address=ContractManager.Cross.address,
        contract_abi=ContractManager.Cross.abi,
        exec_func="setUpdateAlg",
        func_args=(address_update,),
    )
    assert txreceipt.status == 1, f"txfailed! txreceipt: {txreceipt}"


def exec_null():
    ethsdk = EthSdk(url=ETH_URL, poa=True)
    ethsdk.w3.geth.miner.start()
    prepare(ethsdk=ethsdk, alg_case=0)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.Cross)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_BCRUpdate():
    ethsdk = EthSdk(url=ETH_URL, poa=True)
    # deploy BCRUpdate
    ethsdk.w3.geth.miner.start()
    prepare(ethsdk=ethsdk, alg_case=1)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.Cross)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_BCRUpdateOpt():
    ethsdk = EthSdk(url=ETH_URL, poa=True)
    # deploy BCRUpdate
    ethsdk.w3.geth.miner.start()
    prepare(ethsdk=ethsdk, alg_case=2)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.Cross)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_UpdateByLeaves():
    ethsdk = EthSdk(url=ETH_URL, poa=True)
    # deploy UpdateByLeaves
    ethsdk.w3.geth.miner.start()
    prepare(ethsdk=ethsdk, alg_case=3)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.Cross)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_UpdateByTree():
    ethsdk = EthSdk(url=ETH_URL, unlock_genesis=False, poa=True)
    # deploy UpdateByTree
    ethsdk.w3.geth.miner.start()
    prepare(ethsdk=ethsdk, alg_case=4)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.Cross)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--method", 
        type=str, 
        required=True, 
        help="the method names include: null, BCR, UpdateByLeaves, UpdateByTree"
    )
    args = parser.parse_args()
    method = args.method
    if method not in ["null", "BCR", "UpdateByLeaves", "UpdateByTree"]:
        raise ValueError(f"unknown method: {method}")
    return method

def main():
    method = get_args()
    if method == "null":
        exec_null()
    elif method == "BCR":
        exec_BCRUpdateOpt()
    elif method == "UpdateByLeaves":
        exec_UpdateByLeaves()
    elif method == "UpdateByTree":
        exec_UpdateByTree()
    # print("======================= exec_null =======================")
    # exec_null()
    # print("======================= exec_null finish =======================")

    # print("======================= exec_BCRUpdate =======================")
    # exec_BCRUpdate()
    # print("======================= exec_BCRUpdate finish =======================")

    # print("======================= exec_BCRUpdateOpt =======================")
    # exec_BCRUpdateOpt()
    # print("======================= exec_BCRUpdateOpt finish =======================")

    # print("======================= exec_UpdateByLeaves =======================")
    # exec_UpdateByLeaves()
    # print("======================= exec_UpdateByLeaves finish =======================")

    # print("======================= exec_UpdateByTree =======================")
    # exec_UpdateByTree()
    # print("======================= exec_UpdateByTree finish =======================")


if __name__ == "__main__":
    main()
