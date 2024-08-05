# encoding: utf-8

import traceback
import sys
import json

import paramiko

from tools.helper.response_helper import MyResponse
from paramiko.sftp_attr import SFTPAttributes

class Remote(paramiko.SSHClient):
    def __init__(self, host, username, password, port=22):
        super(Remote, self).__init__()
        try:
            self.load_system_host_keys()
            self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.connect(hostname=host, port=port, username=username, password=password, compress=True)
            self.host = host
            self.port = port
            self.username = username
            self.password = password
        except Exception as e:
            self.__close()
            raise Exception(traceback.format_exc())
    
    def __close(self):
        try:
            self.close()
        except:
            pass

    def __del__(self):
        self.__close()
    
    def exec(self, cmd: str, *args, **kwargs) -> MyResponse:
        """        
        return MyResponse:
            msg: stdout.read()
            error: stderr.read()
            code: 101 if stderr else 0
        """
        stdin, stdout, stderr = self.exec_command(cmd, *args, **kwargs)
        error = stderr.read().decode()
        msg = stdout.read().decode()
        code = 101 if error else 0
        return MyResponse(code, msg, error)
    
    def upload(self, localpath, remotepath) -> SFTPAttributes:
        sftpclient = paramiko.SFTPClient.from_transport(self.get_transport())
        remotefileinfo = sftpclient.put(localpath,remotepath)
        return remotefileinfo
        
        


            


    
    
    

        
        
