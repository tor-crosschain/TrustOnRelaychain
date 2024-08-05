import os
import psutil
import subprocess
import random
import json
import time
import re
import signal
from typing import Union

def killlast(piddir):
    pidfile = os.path.join(piddir, 'pid')
    if not os.path.exists(piddir):
        os.makedirs(piddir)
    if not os.path.exists(pidfile):
        return
    with open(pidfile, 'r') as f:
        pid = f.read()
    try:
        pid = int(pid)
    except:
        pid = None
        pass
    if pid and psutil.pid_exists(pid):
        os.kill(int(pid), signal.SIGKILL)

def writepid(piddir, pid):
    pidfile = os.path.join(piddir, 'pid')
    if not os.path.exists(piddir):
        os.makedirs(piddir)
    pidfile = os.path.join(piddir, 'pid')
    with open(pidfile, 'w') as f:
        f.write(str(pid))

def require(condition, error):
    if not condition:
        raise Exception(error)

def exec_command(cmd: str, cmd_type: str):
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
    require(returncode == 0, error="{} failed! error: {}, returncode: {}, cmd: {}".format(cmd_type, err, returncode, cmd))
    return out

def get_random_free_port(ports: list, n=1) -> Union[int, list]:
    cmd = "netstat -nl |grep -v Active| grep -v Proto|awk '{print $4}'|awk -F: '{print $NF}'"
    out = exec_command(cmd, "get listening port")
    out = str(out)
    listening_ports = [ port for port in out.split('\n') if port.strip() ]
    free_ports = []
    for port in ports:
        if str(port) not in listening_ports:
            free_ports.append(int(port))
            if len(free_ports) == n: break
    if len(free_ports) == 1: return free_ports[0]
    if len(free_ports) > 1: return free_ports
    raise Exception("no free port!")

def get_pid_by_condition(*condition) -> list:
    cmd = "ps -uxww | grep -v grep {} | awk '{{print $2}}'".format(
        "".join(
            "| grep '{}' ".format(cdt) for cdt in condition
        )
    )
    out = exec_command(cmd, cmd_type='get pid by condition')
    out = str(out)
    pids = [pid for pid in out.split('\n') if pid.strip()]
    return pids      

def generate_account(geth, datadir):
    pwdfile = os.path.join(datadir, 'pwd')
    os.system("touch {}".format(pwdfile))
    cmd = "{geth} account new --password {pwdfile} --datadir {datadir}".format(geth=geth, pwdfile=pwdfile, datadir=datadir)
    out = exec_command(cmd, 'generate account')
    addrs = re.findall('^Address: \{([a-zA-Z0-9]*)\}',out)
    require(len(addrs) == 1, "generate account error, out: {}, cmd: {}".format(out, cmd))
    return addrs[0]

def generate_bu_config(bupath, genesis_account, validation_account, port_p2p, port_web, port_ws, known_peers):
    buconfig_file = os.path.join(bupath, 'config', 'bumo.json')
    require(os.path.exists(buconfig_file), "{} not exists".format(buconfig_file))
    buconfig = json.load(open(buconfig_file))    
    buconfig['p2p']['consensus_network']['listen_port'] = int(port_p2p)
    buconfig['p2p']['consensus_network']['known_peers'] = list(known_peers)
    buconfig['webserver']['listen_addresses'] = '0.0.0.0:{}'.format(port_web)
    buconfig['wsserver']['listen_address'] = '0.0.0.0:{}'.format(port_ws)
    buconfig['ledger']['validation_address'] = validation_account['address']
    buconfig['ledger']['validation_private_key'] = validation_account['private_key']
    buconfig['genesis']['account'] = genesis_account['address']
    buconfig['genesis']['validators'] = [validation_account['address']]
    json.dump(buconfig, open(buconfig_file, 'w'))



def write_genesis(datadir, genesis_config):
    genesis_path = os.path.join(datadir, 'genesis.json')
    json.dump(
        genesis_config,
        open(genesis_path, 'w')
    )
    return genesis_path

def write_account(datadir, account_files):
    keystore = os.path.join(datadir, 'keystore')
    if not os.path.exists(keystore): os.makedirs(keystore)
    for filename, filecontent in account_files:
        account_file_path = os.path.join(keystore, filename)
        with open(account_file_path, 'w') as f:
            f.write(filecontent)



if __name__ == "__main__":
    # print(get_random_free_port(50000, 50100))
    # print(get_pid_by_condition('python'))
    # generate_genesis_hit('hit', '0xg', 's')
    # generate_genesis_pow('pow', '0xg')
    pass