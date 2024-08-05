import os
import sys
import socket
import subprocess
import setting
import requests
import time
import json
import paramiko
from loguru import logger
from helper.exception_helper import require
from helper.response_helper import MyResponse
from helper.remote_helper import Remote

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

def exec_command(remote: Remote, cmd: str) -> str:
    
    def _exec_command_exception(error: str, command: str) -> str:
        return "exec command error!!!\nerror: {error}\ncommand: {command}".format(
            error=error,
            command=command
        )

    resp = remote.exec(cmd=cmd)
    require(resp.code == 0, _exec_command_exception(resp.error, cmd))
    return resp.msg

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