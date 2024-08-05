import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import subprocess
import setting

def gzip(local_tar, local_files):
    """
    gzip blockchain files to blockchain.tar
    """
    print("gzip starting...")
    subp = subprocess.Popen(
        args=[
            'tar',
            'zcf',
            local_tar,
            local_files
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8'
    )
    subp.wait()
    returncode = subp.poll()
    if returncode != 0:
        raise Exception("gzip failed! error: {}".format(subp.stderr.read()))
    print("gzip finished!")

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath("."))
    from tools.helper.config_client_helper import ConfigClient
    config_name = 'transfer'
    config_client = ConfigClient(config_name=config_name, host=setting.CONFIG_DB_HOST, port=setting.CONFIG_DB_PORT)
    transfer = config_client.get()
    gzip(transfer['local_tar'], transfer['local_files'])
    if not os.path.exists(transfer['local_tar']):
        raise Exception("gzip error")
    else:
        print("gzip suceess")
