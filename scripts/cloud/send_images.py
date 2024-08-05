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

    client.close()
    print("ungzip finished!")

def send_tar(servers: list, transfer_config: dict):
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
        send = server.get('send', True)
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

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath('.'))
    from tools.helper.config_client_helper import ConfigClient
    config_client = ConfigClient(host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    # transfer_config = config_client.get([], config_name='transfer')
    server_config = [
        {
            "host": "122.9.39.32",
            "port": "22",
            "username": "root",
            "password": "nnm2ys*7061",
            "send": True
        },
        {
            "host": "114.116.221.190",
            "port": "22",
            "username": "root",
            "password": "nnm2ys*7061",
            "send": True
        },
        {
            "host": "122.9.33.196",
            "port": "22",
            "username": "root",
            "password": "nnm2ys*7061",
            "send": True
        },
        {
            "host": "114.116.215.14",
            "port": "22",
            "username": "root",
            "password": "nnm2ys*7061",
            "send": True
        }
    ]
    transfer_config = {
        'local_tar': '/home/yiiguo/installer/docker_images/u16py.tar.gz',
        'remote_tar': '/root/u16py.tar.gz',
        'remote_files': ''
    }
    send_tar(server_config, transfer_config)
