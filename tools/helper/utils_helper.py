import os
import sys
import socket
import subprocess
import setting
import requests
import time
import json
import paramiko
import random
import re
import traceback
import shutil
import threading
from typing import Union
from hashlib import sha256
from loguru import logger
from tools.helper.exception_helper import require
from tools.helper.response_helper import MyResponse
from tools.helper.remote_helper import Remote
from tools.sdk.ethsdk import EthSdk

def print_thread(msg: str):
    print("[{thread_name}] {msg}".format(
        thread_name=threading.currentThread().getName(), 
        msg=msg
    ))


def calc_hash(*args, **kwargs):
    calc = sha256()
    args += tuple(kwargs.values())
    for arg in args:
        if not isinstance(arg, bytes):
            arg = str(arg).encode()
        calc.update(arg)
    return calc.hexdigest()

def get_host_ip():
    """
    查询本机ip地址
    :return: ip
    """
    env_ip = os.environ.get('HOSTIP', None)
    if env_ip: return env_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()

    return ip

def get_remote_client(host, port, username, password) -> paramiko.SSHClient:
    client_identify = '{}:{}'.format(host, port)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, port=port, username=username, password=password)
    return client

def shell_call(cmd, shell=False,  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs) -> (bool, str):
    subp = subprocess.Popen(
        args=cmd,
        stdin=stdin, 
        stderr=stderr,
        stdout=stdout,
        shell=shell,
        encoding='utf-8',
        **kwargs
    )
    subp.wait()
    returncode = subp.poll()
    if returncode == 0:
        return True, subp.stdout.read()
    else:
        return False, subp.stderr.read()

def shell_exec(cmd, condition_check: list, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs):
    flag, out = shell_call(cmd, shell=True, **kwargs)
    if not flag: return (False, out, -1)
    cmd_check = 'ps -ux | grep -v "grep" {} | awk \'{{print $2}}\''.format(
        "".join(
            '| grep "{}" '.format(condition) for condition in condition_check
        )
    )
    flag, pid = shell_call(cmd_check, shell=True, **kwargs)
    if not flag: return (False, out, -1)
    return (True, out, pid.strip("\n\r"))

    # subp = subprocess.Popen(
    #     args=cmd,
    #     stdin=stdin,
    #     stderr=stderr,
    #     stdout=stdout,
    #     shell=shell,
    #     encoding='utf-8'
    # )
    # subp.wait()

def get_config() -> dict:
    r = requests.get(
        url=setting.LOCAL_SERVER_URL_GLOBAL_CONFIG
    )
    require(r.status_code == 200, "get config from cloud server error, status_code: {}".format(r.status_code))
    result = MyResponse(r.json())
    require(result.code == 0, "get config from cloud server error, result: {}".format(result.as_dict))
    return result.msg

def exec_command_remote(remote: Remote, cmd: str) -> str:
    
    def _exec_command_exception(error: str, command: str) -> str:
        return "exec command error!!!\nerror: {error}\ncommand: {command}".format(
            error=error,
            command=command
        )

    resp = remote.exec(cmd=cmd)
    require(resp.code == 0, _exec_command_exception(resp.error, cmd))
    return resp.msg

def exec_command_local(cmd: str, cmd_type: str, **kwargs):
    subp = subprocess.Popen(
        args=cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
        **kwargs
    )
    subp.wait()
    out = subp.stdout.read()
    err = subp.stderr.read()
    returncode = subp.poll()
    require(returncode == 0, error="{} failed! error: {}, returncode: {}, cmd: {}".format(cmd_type, err, returncode, cmd))
    return out

def get_free_port() -> int:
    """
    get free port between [60000-6000]
    ssh: 60022
    get from redis zset, key: process_ports
    """
    r = requests.get(
        url=setting.LOCAL_SERVER_URL_NETPORT,
        data={
            'host': get_host_ip()
        }
    )
    require(r.status_code == 200, "get netport from cloud server error, status_code: {}".format(r.status_code))
    result = MyResponse(r.json())
    require(result.code == 0, "get netport from cloud server error, result: {}".format(result.as_dict()))
    return int(result.msg)

def return_result(cmdid: str, resp: str):
    for i in range(3):
        try:
            r = requests.post(
                url=setting.LOCAL_SERVER_URL_RETURN,
                data={
                        'cmdid': cmdid,
                        'resp': resp
                    }
            )
            require(r.status_code == 200, "return result to cloud server error, status_code: {}".format(r.status_code))
            result = MyResponse(r.json())
            require(result.code == 0, "return result to cloud server error, result: {}".format(result.as_dict()))
            return True
        except Exception as e:
            logger.warning("return data failed {} time, error: {}".format(i+1, str(e)))
            time.sleep(1)
    return False

def wait_result(cmdid: str, timeout=10):
    starttime = time.time()
    while time.time() <= starttime + timeout:
        try:
            r = requests.get(
                url=setting.LOCAL_SERVER_URL_RETURN,
                params={'cmdid': cmdid}
            )
            resp = MyResponse(r.json())
            result = json.loads(resp.msg) # get mongo dict
            if len(result) > 0:
                return True, result['resp'] # real result
            else:
                time.sleep(1)
        except Exception as e:
            logger.warning("get result from local server resp failed, error: {}".format(str(e)))
            time.sleep(3)
    return False, {}

def savefile(filepath, content):
    dir_path = os.path.dirname(os.path.abspath(filepath))
    if not isinstance(content, str): content = str(content)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(filepath, 'w') as f:
        f.write(content)
    

def create_account_on_eth(ethSdk: EthSdk, password: str=""):
    print("正在eth上创建新账户......")
    account = ethSdk.newAccount(password=password)
    print("账号已创建，正在向新账户转移10000eth......")
    flag = ethSdk.unlockAccount(account, password, 0)
    if not flag:
        raise Exception("新账户解锁失败! account: {}; password: {}".format(account, password))
    print("新账户解锁完成! account: {}; password: {}".format(account, password))

    return account

def auth_new_hit_account(ethSdk, new_account: str, signer_account: dict, wait=True):
    ethSdk.unlockAccount(signer_account['address'], signer_account['password'], 0)
    if wait:
        receipt = ethSdk.sendSingleTransaction(addr_from=signer_account['address'], addr_to=new_account, value=1, authority="0x66") # auth new account with signer_account
        require(receipt['status'] == 1, "授权失败, hash: {}".format(receipt['transactionHash'].hex()))
        return receipt['transactionHash'].hex()
    else:
        txhash = ethSdk.sendSingleTransaction(addr_from=signer_account['address'], addr_to=new_account, value=1, authority="0x66", wait=False)
        return txhash.hex()

def auth_account(nodes, new_account: Union[str, list]):
    print("准备授权账户: {}".format(new_account))
    txhashes = []
    ethsdk = None
    for idx, node in enumerate(nodes):
        print("签名者({})正在授权......".format(node['signer_account']['address']))
        rpc = 'http://{}:{}'.format(node['host'], node['rpcport'])
        ethsdk = EthSdk(rpc, poa=True, unlock_genesis=False)
        if isinstance(new_account, str):
            new_account = [new_account]
        for account in new_account:
            txhash = auth_new_hit_account(ethsdk, account, node['signer_account'], wait=False)
            txhashes.append(txhash)
    
    if ethsdk is not None:
        print("wait receipt......")
        time0 = time.time()
        for txhash in txhashes:
            txreceipt = ethsdk.w3.eth.waitForTransactionReceipt(txhash)
            if txreceipt['status'] != 1:
                raise Exception("auth failed! txhash: {}".format(txhash))
            print("get receipt, txhash: {}".format(txreceipt['transactionHash']))
        print("账户({})已经被授权! cost time: {}".format(new_account, time.time()-time0))


def create_account_on_bu(busdk):
    print("正在bu上创建账户......")
    account, err = busdk.generateAccount()
    if err != '':
        raise Exception('parallel_create_default_account_bu err!:{}'.format(err))
    bu = 1e14
    print("账号已创建，正在向新账户转移 {} bu......".format(bu))
    busdk.payCoin(busdk.genesisAccount,account['address'],bu,contract_input={}) # payCoin, 如果目标账户不存在则直接创建
    print("账号创建完成，详细信息：{}".format(account))
    return account

def generate_genesis_poa(genesis_path: str, genesis_account: str, signer_account: Union[str, list], period=5, gasLimit='0xffffffffffffffff'):
    genesis = {
        'config': {},
        'alloc': {},
    }
    genesis_account = str(genesis_account)[2:] if str(genesis_account).startswith('0x') else str(genesis_account)
    genesis['alloc'] = {
        genesis_account: {
            'balance': "0x2000000000000000000000000000000000000000000000000000000000000000",
        },
    }
    if isinstance(signer_account, str):
        signer_account = [signer_account]
    signer_account = [
        str(signer)[2:] if str(signer).startswith('0x') else str(signer) 
        for signer in signer_account
    ]
    for signer in signer_account:
        genesis['alloc'][signer] = {
            'balance': "0x2000000000000000000000000000000000000000000000000000000000000000",
        }
    genesis['config'] = {
        "chainId": 31317,
        "homesteadBlock": 0,
        "eip150Block": 0,
        "eip155Block": 0,
        "eip158Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0,
        "istanbulBlock": 0,
        "berlinBlock": 0,
        "clique": {
            "period": 5,
            "epoch": 30000
        }
    }
    genesis.update({
        "nonce": "0x0",
        "timestamp": hex(int(time.time())),
        "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000{}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000".format(
            ''.join(signer_account)
        ),
        "gasLimit": gasLimit,
        "difficulty": "0x1",
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase": "0x0000000000000000000000000000000000000000",
        "number": "0x0",   
        "gasUsed": "0x0",
        "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000"
    })
    json.dump(genesis, open(genesis_path, 'w'))


def generate_genesis_hit(genesis_path: str, genesis_account: str, signer_account: Union[str, list], period=5, gasLimit='0xffffffffffffffff'):
    genesis = {
        'config': {},
        'alloc': {},
    }
    genesis_account = str(genesis_account)[2:] if str(genesis_account).startswith('0x') else str(genesis_account)
    genesis['alloc'] = {
        genesis_account: {
            'balance': "0x2000000000000000000000000000000000000000000000000000000000000000",
            'authority': "0x8000000000000000000000000000000000000000000000000000000000000000"
        },
    }
    if isinstance(signer_account, str):
        signer_account = [signer_account]
    signer_account = [
        str(signer)[2:] if str(signer).startswith('0x') else str(signer) 
        for signer in signer_account
    ]
    for signer in signer_account:
        genesis['alloc'][signer] = {
            'balance': "0x2000000000000000000000000000000000000000000000000000000000000000",
            'authority': "0x0"
        }
    genesis['config'] = {
        "chainId": 31317,
        "homesteadBlock": 1,
        "eip150Block": 2,
        "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "eip155Block": 3,
        "eip158Block": 3,
        "byzantiumBlock": 1,
        "clique": {
            "period": 5,
            "epoch": 30000
        }
    }
    genesis.update({
        "nonce": "0x0",
        "timestamp": hex(int(time.time())),
        "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000{}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000".format(
            ''.join(signer_account)
        ),
        "gasLimit": gasLimit,
        "difficulty": "0x1",
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "coinbase": "0x0000000000000000000000000000000000000000",
        "number": "0x0",   
        "gasUsed": "0x0",
        "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000"
    })
    json.dump(genesis, open(genesis_path, 'w'))

def generate_genesis_pow(genesis_path: str, genesis_account: str, difficulty="0x400000", gasLimit='0xffffffff'):
    genesis = {
        'config': {},
        'alloc': {},
    }
    
    genesis_account = genesis_account[2:] if genesis_account.startswith('0x') else genesis_account
    genesis['alloc'] = {
        genesis_account: {
            'balance': "0x2000000000000000000000000000000000000000000000000000000000000000",
        }
    }
    genesis['config'] = {
        "chainId": random.randint(100, 10000),
        "homesteadBlock": 0,
        "eip155Block": 0,
        "eip158Block": 0,
        "eip150Block": 0,
        "byzantiumBlock": 0,
        "constantinopleBlock": 0,
        "petersburgBlock": 0
    }
    genesis.update({
        "coinbase"   : "0x0000000000000000000000000000000000000000",
        "difficulty" : difficulty, 
        "extraData"  : "",
        "gasLimit"   : gasLimit,
        "nonce"      : "0x0000000000000042",
        "mixhash"    : "0x0000000000000000000000000000000000000000000000000000000000000000",
        "parentHash" : "0x0000000000000000000000000000000000000000000000000000000000000000",
        "timestamp"  : "0x00",
    })
    json.dump(genesis, open(genesis_path, 'w'))



def generate_account(geth, datadir, password=''):
    pwdfile = os.path.join(datadir, 'pwd'+str(int(time.time()*1000)))
    os.system("echo -n '{password}' > {pwdfile}".format(password=password, pwdfile=pwdfile))
    try:
        cmd = "{geth} account new --password {pwdfile} --datadir {datadir}".format(geth=geth, pwdfile=pwdfile, datadir=datadir)
        out = exec_command_local(cmd, 'generate account')
        addrs = re.findall('^Address: \{([a-zA-Z0-9]*)\}',out)
        require(len(addrs) == 1, "generate account error, out: {}, cmd: {}".format(out, cmd))
    except Exception as e:
        raise Exception(traceback.format_exc())
    finally:
        os.remove(pwdfile)
    addr = addrs[0]
    if len(addr) % 2 == 1: addr = '0'+addr
    return '0x'+addr

def generate_account_bu(bupath):
    bumo = os.path.join(bupath, 'bin', 'bumo')
    if not os.path.exists(bumo): raise Exception("{} is invalid".format(bumo))
    cmd = "{bumo} --create-account".format(bumo=bumo)
    subp = subprocess.Popen(
        args=cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
    )
    subp.wait()
    out = subp.stdout.read()
    err = subp.stderr.read()
    returncode = subp.poll()
    account = json.loads(out)
    require(
        account.get('address', None) and account.get('private_key', None) and account.get('public_key', None),
        "account is wrong, account: {}".format(account)
    )
    return account

def gen_account(geth_path, password=''):
    temp_data_dir = './temp_datadir_'+str(time.time()*1000)[-5:]
    if os.path.exists(temp_data_dir): 
        shutil.rmtree(temp_data_dir)
    os.makedirs(temp_data_dir)
    try:
        account = generate_account(geth=geth_path,datadir=temp_data_dir,password=password)
        keystore_path = os.path.join(temp_data_dir, 'keystore')
        account_file_name = os.listdir(keystore_path)[0]
        account_file = os.path.join(keystore_path, account_file_name)
        with open(account_file, 'r') as f:
            account_file_content = f.read()
        account_file = (account_file_name, account_file_content)
    except Exception as e:
        raise Exception(traceback.format_exc())
    finally:
        shutil.rmtree(temp_data_dir)
    return account, account_file