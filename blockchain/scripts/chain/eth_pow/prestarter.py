import os
import sys
import json
import subprocess
import utils
from scripts import setting

if False:
    import blockchain.scripts.utils as utils

def start(idx, root_dir, bootnode_path, bootnode_key, hostip, port, cache_pid_dir):
    if not os.path.exists(bootnode_path):
        raise Exception("executable bootnode binary not exists!")
    bootnode_data = os.path.join(root_dir, 'bootnode', idx)
    if not os.path.exists(bootnode_data):
        os.makedirs(bootnode_data)
    key = bootnode_key
    os.system('cd {bootnode_data} && {bootnode} -genkey {key}'.format(bootnode_data=bootnode_data, bootnode=bootnode_path, key=key))
    keyfile = os.path.join(bootnode_data, key)

    logpath = os.path.join(bootnode_data, 'bootnode{idx}.log'.format(idx=idx))
    subp = subprocess.Popen(
        args='cd {bootnode_data} && nohup {bootnode} -nodekey {keyfile} -addr :{port} -verbosity 9 > {logpath} 2>&1 &'.format(
            bootnode_data=bootnode_data,
            bootnode=bootnode_path,
            port=port,
            keyfile=keyfile,
            logpath=logpath
        ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding='utf-8'
    )
    subp.wait()
    out = subp.stdout.read()
    err = subp.stderr.read()
    returncode = subp.poll()
    if returncode != 0:
        raise Exception("bootnode start failed! error: {}".format(err))
    process = subprocess.run(
        args='cd {bootnode_data} && {bootnode} -writeaddress -nodekey {keyfile}'.format(bootnode_data=bootnode_data, bootnode=bootnode_path, keyfile=keyfile),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        encoding='utf-8'
    )
    process.check_returncode()
    secretkey = process.stdout.strip('\n')
    enode_info = "enode://{secretkey}@{hostip}:{port}".format(secretkey=secretkey,hostip=hostip,port=port)
    pids = utils.get_pid_by_condition(bootnode_path, port, keyfile)
    return enode_info, pids[0]

def prestart(idx, chain_config: dict):
    bootnode_key = chain_config.get('bootnode_key', None)
    if not bootnode_key:
        raise Exception("bootnode_key cannot be None!")
    cache_pid_dir = '/root/workspace/cache_pid'
    piddir = os.path.join(cache_pid_dir, 'bootnode', idx)
    utils.killlast(piddir)
    # TODO 从配置文件里面读取可用端口
    pre_ports = setting.PORTS_RANGE # open port with UDP
    hostip = os.environ['HOSTIP'] # set env HOSTIP when running docker container
    port = utils.get_random_free_port(pre_ports)
    root_dir = '/root/workspace/blockchain'
    bootnode_path = '{}/bin/bootnode'.format(root_dir)
    enode_info, pid = start(idx, root_dir, bootnode_path, bootnode_key, hostip, port, cache_pid_dir)
    utils.writepid(piddir, pid=pid)
    return enode_info
    