from __future__ import annotations
import os, sys
import re

sys.path.insert(0, os.path.abspath("."))
import subprocess
from utils.ethsdk import EthSdk
from typing import List
from web3.types import TxReceipt
import math, json

ETH_PORT = 60001
ETH_URL = f"http://127.0.0.1:{ETH_PORT}"
LEAVESNUM = 1000
OUTPUT_FILE = "./bcr/result/data_{name}.json"
os.environ["SOLC_BINARY"] = "./bin/solc_0.8.2"
average = lambda x: sum(x) / len(x)


class ContractInfo:
    def __init__(self) -> None:
        self.abi = ""
        self.opcode = 0x00
        self.filepath = ""
        self.name = ""
        self.address = ""

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
    cmd = """ ssh yiiguo@10.21.162.162 -p 50022 "{}" """.format(
        "docker exec test_crosschain /bin/bash -c \\\"cat /root/workspace/blockchain/parallel_chain/0/start.log | grep 'yiiguo applyTransaction'\\\""
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
            exec_func="build",
            func_args=[1, int.to_bytes(i, length=2, byteorder="big")],
            source_args={"gas": 5000000},
            wait=False,
        )[0].hex()
        for i in range(LEAVESNUM)
    ]
    sdk.w3.geth.miner.start()
    print("wait merkle build receipts...")
    receipts: List[TxReceipt] = [
        sdk.waitForTransactionReceipt(txhash=txhash) for txhash in txhashes
    ]
    BATCH_SIZE = int(math.sqrt(LEAVESNUM))
    gasUseds = [receipt["gasUsed"] for receipt in receipts]
    gasUseds_batch = [
        average(gasUseds[i : i + BATCH_SIZE])
        for i in range(0, len(gasUseds), BATCH_SIZE)
    ]
    print(f"gasUsed batch: {gasUseds_batch}")
    average_gas = sum(gasUseds) / len(gasUseds)
    print(f"block number: {set(receipt['blockNumber'] for receipt in receipts)}")
    durs = get_durs(txhashes=txhashes)
    durs_batch = [
        average(durs[i : i + BATCH_SIZE]) for i in range(0, len(durs), BATCH_SIZE)
    ]
    print(f"durs batch: {durs_batch}")
    print(f"durs length: {len(durs)}")
    # assert len(durs) == len(txhashes), f"durs: {durs}"
    average_dur = sum(durs) / len(durs)
    json.dump(
        obj={
            "gasUseds": gasUseds,
            "durs": durs,
            "average_gas": average_gas,
            "average_dur": average_dur,
        },
        fp=open(OUTPUT_FILE.format(name=cinfo.name), "w"),
    )
    return average_gas, average_dur


def exec_BCRUpdate():
    ethsdk = EthSdk(url=ETH_URL)
    # deploy BCRUpdate
    ethsdk.w3.geth.miner.start()
    address, abi = ethsdk.compileAndDeploy(
        contractfile=ContractManager.BCRUpdate.filepath,
        contract_name=ContractManager.BCRUpdate.name,
    )
    ContractManager.BCRUpdate.set_address(address).set_abi(abi)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.BCRUpdate)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_BCRUpdateOpt():
    ethsdk = EthSdk(url=ETH_URL)
    # deploy BCRUpdate
    ethsdk.w3.geth.miner.start()
    address, abi = ethsdk.compileAndDeploy(
        contractfile=ContractManager.BCRUpdateOpt.filepath,
        contract_name=ContractManager.BCRUpdateOpt.name,
    )
    ContractManager.BCRUpdateOpt.set_address(address).set_abi(abi)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.BCRUpdateOpt)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_UpdateByLeaves():
    ethsdk = EthSdk(url=ETH_URL)
    # deploy UpdateByLeaves
    ethsdk.w3.geth.miner.start()
    address, abi = ethsdk.compileAndDeploy(
        contractfile=ContractManager.UpdateByLeaves.filepath,
        contract_name=ContractManager.UpdateByLeaves.name,
    )
    ContractManager.UpdateByLeaves.set_address(address).set_abi(abi)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.UpdateByLeaves)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def exec_UpdateByTree():
    ethsdk = EthSdk(url=ETH_URL)
    # deploy UpdateByTree
    ethsdk.w3.geth.miner.start()
    address, abi = ethsdk.compileAndDeploy(
        contractfile=ContractManager.UpdateByTree.filepath,
        contract_name=ContractManager.UpdateByTree.name,
    )
    ContractManager.UpdateByTree.set_address(address).set_abi(abi)
    average_gas, average_dur = measure(sdk=ethsdk, cinfo=ContractManager.UpdateByTree)
    print(f"average_gas: {average_gas}, average_dur: {average_dur}")


def main():
    # get_durs(["0x98a6bf6b0d1db70ba9c6d5f950a79c0700e97d2baa9e0b9f641b4df077c034b0"])
    # print("======================= exec_BCRUpdate =======================")
    # exec_BCRUpdate()
    # print("======================= exec_BCRUpdate finish =======================")

    # print("======================= exec_BCRUpdateOpt =======================")
    # exec_BCRUpdateOpt()
    # print("======================= exec_BCRUpdateOpt finish =======================")

    print("======================= exec_UpdateByTree =======================")
    exec_UpdateByTree()
    print("======================= exec_UpdateByTree finish =======================")

    # print("======================= exec_UpdateByLeaves =======================")
    # exec_UpdateByLeaves()
    # print("======================= exec_UpdateByLeaves finish =======================")


if __name__ == "__main__":
    main()
