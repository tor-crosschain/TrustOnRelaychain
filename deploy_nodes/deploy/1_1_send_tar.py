import os, sys
sys.path.insert(0, os.path.abspath('.'))
import time
import paramiko
import setting
import threading
from tools.helper.utils_helper import get_remote_client

def upload(host, port, username, password, local_tar, remote_tar, remote_files, send=True):
    print("upload to host: {}......".format("{}:{}".format(host, port)))
    client = get_remote_client(host, port, username, password)
    print("connect!")
    if send:
        sftp = client.open_sftp()
        _ = sftp.put(local_tar, remote_tar)
        print("transport blockchain.tar success!")
    command="cd /root/workspace && rm -rf {remote_files_old} && tar xzvf {remote_tar}".format(
            remote_files_old=remote_files,
            remote_tar=remote_tar
        )
    # if not master:
    #     # if this node(host:port) is not master node, then delete the genesis-keystore files
    #     command = "{} && find . -name \"keystore\" -type d | xargs rm -rf ".format(command)
    stdin, stdout, stderr = client.exec_command(
        command=command
    )
    out = stdout.read().decode().strip(" \n\r")
    err = stderr.read().decode().strip(" \n\r")
    if err:
        raise Exception("ungzip failed! host: {}, port:{}, err: {}".format(host, port, err))
    client.close()
    print("ungzip finished!")

def send_tar(servers: dict, transfer_config: dict, send: bool):
    """
    send tar to remote_path
    """
    print("ready to transport blockchian.tar to remote server!")
    master = False
    local_tar = transfer_config['local_tar']
    remote_tar = transfer_config['remote_tar']
    remote_files = transfer_config['remote_files']
    
    """
    TODO 加个字段，判断是否应该 send
    """
    threads = []
    start = time.time()
    for idx, server in enumerate(servers):
        host = server['host']
        port = server['port']
        username = server['username']
        password = server['password']
        send = server.get('send', True) and send
        threads.append(
            threading.Thread(
                target=upload, args=[host, port, username, password, local_tar, remote_tar, remote_files, send]
            )
        )
        # upload(host, port, username, password, local_tar, remote_tar, remote_files)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    end = time.time()
    print("blockchain.tar transportation finished! cost: {}".format(end-start))

def getArgs():
    import argparse
    parser = argparse.ArgumentParser()
    flag_parser = parser.add_mutually_exclusive_group(required=False)
    flag_parser.add_argument('--send', dest='send', action='store_true')
    flag_parser.add_argument('--no-send', dest='send', action='store_false')
    parser.set_defaults(send=True)
    return parser.parse_args()

if __name__ == "__main__":
    args = getArgs()
    print(args.send)
    import os, sys
    sys.path.insert(0, os.path.abspath('.'))
    from tools.helper.config_client_helper import ConfigClient
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    transfer_config = config_client.get([], config_name='transfer')
    server_config = config_client.get([], config_name='server')
    # server_config = config_client.get(['chain', 'server_nodes'], config_name='test_hit_tps_labserver')
    
    send_tar(server_config, transfer_config, args.send)
