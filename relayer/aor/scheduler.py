from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.abspath("."))
import argparse
import time
import setting
import json
import threading
import multiprocessing
from loguru import logger
from eth_account import Account
from typing import List, Dict
from tools.helper.config_client_helper import ConfigClient
from tools.helper.utils_helper import exec_command_local
from tools.sdk.ethsdk import EthSdk

payloads_path = "./payloads/aor"
if not os.path.exists(payloads_path):
    os.makedirs(payloads_path)

def start_gateways_from_para_to_relay_local(config_name: str, chain_configs: List[dict], tag):
    relay_chain_id = 0
    
    # transfer to new account on thr relay chain
    keys = [0]*len(chain_configs)
    relay_node = chain_configs[0]['server_nodes'][0]
    url = f"http://{relay_node['host']}:{relay_node['rpcport']}"
    ethsdk = EthSdk(url=url, poa=True, unlock_genesis=False)
    transferHashes = []
    for chain_id, config in enumerate(chain_configs):
        if chain_id == relay_chain_id: continue
        header_account = Account.create()
        header_key = header_account.key.hex()
        header_address = header_account.address
        txhash = ethsdk.sendSingleTransaction(
            addr_from=ethsdk.defaultAccount,
            addr_to=header_address,
            value=ethsdk.toWei(1),
            wait=False
        )
        transferHashes.append(txhash)
        print(f"transfer to header account({header_address}) ok!")

        tx_account = Account.create()
        tx_key = tx_account.key.hex()
        tx_address = tx_account.address
        txhash = ethsdk.sendSingleTransaction(
            addr_from=ethsdk.defaultAccount,
            addr_to=tx_address,
            value=ethsdk.toWei(1),
            wait=False
        )
        transferHashes.append(txhash)
        print(f"transfer to tx account({tx_address}) ok!")

        keys[chain_id] = (header_key, tx_key)

    for txhash in transferHashes:
        receipt = ethsdk.waitForTransactionReceipt(txhash)
        assert receipt["status"] == 1
        print(f"wait receipt ok! txhash: {txhash.hex()}")

    cmds = []
    logpath = "logs/aor"
    if not os.path.exists(logpath):
        os.makedirs(logpath)
    # start relayer from parachains to the relay chain
    timestamp = int(time.time())
    for chain_id, config in enumerate(chain_configs):
        if chain_id == relay_chain_id: continue
        header_key, tx_key = keys[chain_id]
        relay_identifier = f"relay_aor_{timestamp}_{chain_id}_{relay_chain_id}.log"
        cmd = f"nohup python -u relayer/aor/gateway_from_para_to_relay.py --srcid {chain_id} --dstid {relay_chain_id} --header_private_key '{header_key}' --tx_private_key '{tx_key}' --config_name '{config_name}' --tag '{tag}' >{logpath}/{relay_identifier} 2>&1 &"
        cmds.append(cmd)
    for cmd in cmds:
        out = exec_command_local(cmd=cmd, cmd_type="start relayer from parachain to relay", close_fds=True)
        print(cmd)
        print(out, out == '\r\n')

def start_gateways_from_relay_to_para_local(config_name: str, chain_configs: List[dict], tag):
    relay_chain_id = 0
    
    # transfer to new account on parachains
    keys_para = [0]*len(chain_configs)
    def create(chain_id, config, keys_para):
        transferHashes = []
        node = config['server_nodes'][0]
        url = f"http://{node['host']}:{node['rpcport']}"
        ethsdk = EthSdk(url=url, poa=True, unlock_genesis=False)
        # header account
        account = Account.create()
        header_key = account.key.hex()
        tx_key = account.key.hex()        
        address = account.address
        txhash = ethsdk.sendSingleTransaction(
            addr_from=ethsdk.defaultAccount,
            addr_to=address,
            value=ethsdk.toWei(1),
            wait=False
        )
        transferHashes.append(txhash)
        print(f"transfer to tx account({address}) ok!")
        # tx account
        tx_account = Account.create()
        tx_key = tx_account.key.hex()
        tx_address = tx_account.address
        txhash = ethsdk.sendSingleTransaction(
            addr_from=ethsdk.defaultAccount,
            addr_to=tx_address,
            value=ethsdk.toWei(1),
            wait=False
        )
        transferHashes.append(txhash)
        print(f"transfer to tx account({tx_address}) ok!")
        # wait receipts
        for txhash in transferHashes:
            receipt = ethsdk.waitForTransactionReceipt(txhash)
            assert receipt["status"] == 1
            print(f"wait receipt ok! txhash: {txhash.hex()}")

        keys_para[chain_id] = (header_key, tx_key)
    threads = []
    for chain_id, config in enumerate(chain_configs):
        if chain_id == relay_chain_id: continue
        threads.append(threading.Thread(target=create, args=(chain_id, config, keys_para)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    # start gateway from the relay chain to parachains
    timestamp = int(time.time())
    cmds = []
    logpath = "logs/aor"
    if not os.path.exists(logpath):
        os.makedirs(logpath)
    for chain_id, config in enumerate(chain_configs):
        if chain_id == relay_chain_id: continue
        header_key, tx_key = keys_para[chain_id]
        relay_identifier = f"relay_aor_{timestamp}_{relay_chain_id}_{chain_id}.log"
        cmd = f"nohup python -u relayer/aor/gateway_from_relay_to_para.py --srcid {relay_chain_id} --dstid {chain_id} --header_private_key '{header_key}' --tx_private_key '{tx_key}' --config_name '{config_name}' --tag '{tag}' >{logpath}/{relay_identifier} 2>&1 &"
        cmds.append(cmd)
    for cmd in cmds:
        out = exec_command_local(cmd=cmd, cmd_type="start aor relayer from relay to parachain", close_fds=True)
        print(cmd)
        print(out, out == '\r\n')
    

def send_cm_local(config_name, chain_configs: List[dict], each_num: int):
    relay_chain_id = 0
    def send_cm_to_each_chain(chain_id, config):
        logger.add(f"scheduler_log_aor/send_cm_chain_{chain_id}.log")
        logger.info(f"send cross-chain message to chain-{chain_id}")
        node = config['server_nodes'][0]
        url = f"http://{node['host']}:{node['rpcport']}"
        contract_address = config['contract_address']
        contract_abi = json.loads(config['contract_abi'])
        ethsdk = EthSdk(url=url, poa=True, unlock_genesis=False)

        # init count on parachains for wait_finish()
        receipt, _ = ethsdk.contract_transact(
            contract_address=contract_address,
            contract_abi=contract_abi,
            exec_func='resetCountOnDst',
            func_args=[]
        )
        assert receipt['status'] == 1

        payloads = []
        
        # send cross-chain messages
        txhashes = []
        dst_chain_ids = list(range(1, len(chain_configs)))
        dst_chain_ids.remove(chain_id)
        dst_chain_num = len(dst_chain_ids)
        for i in range(each_num):
            dst_chain_id = dst_chain_ids[i%dst_chain_num]
            timestamp = int(time.time()*1000)
            payload = f'targetData-{i+1}-{chain_id}-{dst_chain_id}-{timestamp}'
            payloads.append(payload)
            txhash, _ = ethsdk.contract_transact(
                contract_address=contract_address,
                contract_abi=contract_abi,
                exec_func='crossSend',
                func_args=[
                    chain_id, dst_chain_id, contract_address, contract_address, b'targetFunc', payload.encode()
                ],
                wait=False
            )
            txhashes.append(txhash)
            if (i+1)%10 == 0:
                logger.info(f"send cross-chain message on chain-{chain_id} count: {i+1}")
            time.sleep(0.01)
        logger.info(f"wait receipt on chain-{chain_id}")
        height_set = set()
        for txhash in txhashes:
            receipt = ethsdk.waitForTransactionReceipt(txhash)
            height_set.add(receipt['blockNumber'])
            logger.info(f"get receipt, status: {receipt['status']}")
        logger.info(f"get all receipts on chain-{chain_id}, block_height: {height_set}")

        write_path = os.path.join(payloads_path, config_name)
        if not os.path.exists(write_path):
            os.makedirs(write_path)
        json.dump(payloads, fp=open(f"{write_path}/{chain_id}.ignore.json", 'w'))

    procs: List[multiprocessing.Process] = []
    for chain_id, config in enumerate(chain_configs):
        if chain_id == 0: continue
        proc = multiprocessing.Process(target=send_cm_to_each_chain, args=(chain_id, config))
        procs.append(proc)
    
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()

def wait_finish(chain_configs, target: int):
    wait_start = time.time()
    counts = [0] * len(chain_configs)
    logger.add(f"scheduler_log_aor/wait_finish.log")
    def check(chain_id, config):
        node = config['server_nodes'][0]
        url = f"http://{node['host']}:{node['rpcport']}"
        contract_address = config['contract_address']
        contract_abi = json.loads(config['contract_abi'])
        ethsdk = EthSdk(url=url, poa=True, unlock_genesis=False)
        starttime = 0
        logger.info(f"wait cross-chain messages on chain-{chain_id}")
        while True:
            countOnDst = ethsdk.contract_call(
                contract_address=contract_address,
                contract_abi=contract_abi,
                exec_func='getCountOnDst',
                func_args=[]
            )
            if countOnDst != counts[chain_id]:
                logger.info(f"chain-{chain_id} count change: {countOnDst}")
            counts[chain_id] = countOnDst
            allcount = sum(counts)
            if allcount >= target:
                if starttime == 0:
                    logger.info(f"chain-{chain_id} count sum reach: {allcount}. start to wait more")
                    starttime = time.time()
                elif time.time() - starttime > 10: # run more 10 seconds
                    break
            time.sleep(1) # check with epoch of 1 second

    threads = []
    for chain_id, config in enumerate(chain_configs):
        if chain_id == 0: continue
        threads.append(threading.Thread(
            target=check,
            args=(chain_id, config)
        ))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    costtime = time.time()-wait_start
    print(f"obtain cross-chain messages total {sum(counts)}! cost: {costtime}")

def statistical(config_name, chain_configs):
    read_path = os.path.join(payloads_path, config_name)
    payloads_time = {} # key: {i+1}-{chain_id}-{dst_chain_id}; value: timestamp
    # f'targetData-{i+1}-{chain_id}-{dst_chain_id}-{timestamp}'
    for i in range(1, len(chain_configs)):
        filename = f"{read_path}/{i}.ignore.json"
        payloads: List[str] = json.load(fp=open(filename, 'r'))
        for payload in payloads:
            _, index, chain_id, dst_chain_id, timestamp = payload.split("-")
            key = f"{index}-{chain_id}-{dst_chain_id}"
            payloads_time[key] = int(timestamp)/1000
    
    # execute in thread
    dst_payloads_time = {}
    payloads_latency = {}
    def query_on_each_chain(config):
        node = config['server_nodes'][0]
        url = f"http://{node['host']}:{node['rpcport']}"
        contract_address = config['contract_address']
        contract_abi = json.loads(config['contract_abi'])
        ethsdk = EthSdk(url=url, poa=True, unlock_genesis=False)
        countOnDst = ethsdk.contract_call(
            contract_address=contract_address,
            contract_abi=contract_abi,
            exec_func='getCountOnDst',
            func_args=[]
        )
        blockTs = {}
        for i in range(1, countOnDst+1):
            result = ethsdk.contract_call(
                contract_address=contract_address,
                contract_abi=contract_abi,
                exec_func='getDstCMByCount',
                func_args=[i]
            )
            # print(result)
            payload = result[0][3][2].decode()
            height = int(result[-1])
            ts = blockTs.get(height, None)
            if ts is None:
                block = ethsdk.w3.eth.get_block(height)
                ts = block['timestamp']
                blockTs[height] = ts
            # print(f"timestamp: {ts}")
            _, index, chain_id, dst_chain_id, timestamp = payload.split("-")
            key = f"{index}-{chain_id}-{dst_chain_id}"
            dst_payloads_time[key] = ts
            payloads_latency[key] = ts-payloads_time[key]

    # query cross-chain messages confirmed on the dst parachains
    threads = []
    for chain_id, config in enumerate(chain_configs):
        threads.append(
            threading.Thread(target=query_on_each_chain, args=(config, ))
        )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    avg = lambda x: sum(x)/len(x)
    latency_average = avg(list(payloads_latency.values()))
    latency_max = max(list(payloads_latency.values()))
    latency_min = min(list(payloads_latency.values()))
    initial_time = min(list(payloads_time.values()))
    final_time = max(list(dst_payloads_time.values()))
    
    allcm = len(payloads_time)
    cost = (final_time-initial_time)
    tps = allcm/cost

    json.dump(obj={
        'src': payloads_time,
        'dst': dst_payloads_time,
        'latencys': payloads_latency,
        'latency_average': latency_average,
        'latency_max': latency_max,
        'latency_min': latency_min,
        'tps': tps,
        'cm_num': allcm,
        'cost': cost
    },fp=open(f"{read_path}/output.json", 'w'))

def statistical_info(config_name, chain_configs, tag):
    info_root_path = f"info/aor/{config_name}/{tag}"
    info_allchains_path = f"info/aor/{config_name}/{tag}/allchains"

    clean_data = {
        'crossSend': [], # from user
        'SubmitHeader': [], # from relay to parachain
        'crossReceiveFromRelay': [], # from  para to para
        'SubmitHeaderToRelay': [], # header from para to relay
        'crossReceiveOnRelay': [], # msg from para to relay
    }

    for i in range(1, len(chain_configs)):
        filename = os.path.join(info_allchains_path, f'{i}-{0}-info.ignore.json')
        if not os.path.exists(filename): continue
        infos: List[Dict[str, int]] = json.load(fp=open(filename, 'r'))
        for info in infos:
            key = list(info.keys())[0]
            gas = info[key]
            srcid,fn,txhash = key.split('-')
            if fn not in clean_data: continue
            clean_data[fn].append(gas)
        
    result = {}
    avg = lambda x: sum(x)/len(x)
    for key in list(clean_data.keys()):
        result[key] = avg(clean_data[key])
    filename = os.path.join(info_root_path, 'output.ignore.json')
    json.dump(result, fp=open(filename, 'w'))

def main():
    args = get_args()
    config_name = args.config_name
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT, config_name=config_name)
    chain_configs = config_client.get()
    each_num = 1000
    start_gateways_from_para_to_relay_local(config_name, chain_configs, tag=str(each_num))
    start_gateways_from_relay_to_para_local(config_name, chain_configs, tag=str(each_num))
    start = time.time()
    send_cm_local(config_name, chain_configs, each_num)
    target = (len(chain_configs)-1) * each_num
    wait_finish(chain_configs, target)
    end = time.time()
    print(f"cost: {end-start-10}") # in wait_finish(), wait more 10s
    statistical(config_name, chain_configs) 
    os.system("pkill -f 'gateway_from'")
    statistical_info(config_name, chain_configs, tag=str(each_num))
    
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_name", type=str, required=True)
    return parser.parse_args()

if __name__ == "__main__":
    main()