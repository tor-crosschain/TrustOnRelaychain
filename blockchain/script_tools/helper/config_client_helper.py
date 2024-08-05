import os, sys
sys.path.insert(0, os.path.abspath('.'))
import requests
import json
from typing import Union
from tools.helper.response_helper import MyResponse

if False:
    from tools.helper.response_helper import MyResponse


def require(condition: bool, error: str):
    if not condition:
        raise Exception(error)

class ConfigClient(object):
    def __init__ (self, host='localhost', port=10051, config_name=None):
        self.url = 'http://{}:{}/config'.format(host, port)
        self.config_name = config_name
    
    def __make_request(self, method, key_chain: list, value=None, config_name=None):
        config_name = self.config_name if not config_name else config_name
        require(config_name, "config_name must be assigned!")
        print("config_name: {}".format(config_name))
        if method in ['get']:
            result = requests.get(
                self.url,
                params={
                    'key_chain': json.dumps(key_chain),
                    'config_name': config_name
                }
            )
        else:
            result = requests.post(
                self.url,
                data={
                    'key_chain': json.dumps(key_chain),
                    'value': json.dumps(value),
                    'method': method,
                    'config_name': config_name
                }
            )
        require(result.status_code == 200, 'request error, status_code: {}'.format(result.status_code))
        resp = MyResponse(result.json())
        require(resp.code==0,'response content: {}'.format(resp.as_str()))
        return resp.msg
        

    def __check_key(self, key_chain: list):
        """
        客户端只检查 key_chain 的类型，value 的类型检查放到服务器端来做更加方便
        """
        for key in key_chain:
            require(
                isinstance(key, str) or isinstance(key, int),
                "type of key must be str or int, but get [{}: {}]".format(key, type(key))
            )

    def get(self, key_chain: list=None, config_name: str=None):
        if not key_chain: key_chain = []
        self.__check_key(key_chain)
        return self.__make_request('get', key_chain=key_chain, config_name=config_name)

    def additem(self, value: Union[bool, int, float, str, list, dict], key_chain: list=None, config_name: str=None):
        if not key_chain: key_chain = []
        self.__check_key(key_chain)
        self.__make_request('additem', key_chain=key_chain, value=value, config_name=config_name)
    
    def update(self, value: Union[bool, int, float, str, list, dict], key_chain: list=None, config_name: str=None):
        if not key_chain: key_chain = []
        self.__check_key(key_chain)
        self.__make_request('update', key_chain=key_chain, value=value, config_name=config_name)
    
    def remove(self, key_chain: list=None, config_name: str=None):
        if not key_chain: key_chain = []
        self.__check_key(key_chain)
        self.__make_request('remove', key_chain=key_chain, config_name=config_name)
    
    def append(self, value: Union[bool, int, float, str, list, dict], key_chain: list=None, config_name: str=None):
        if not key_chain: key_chain = []
        self.__check_key(key_chain)
        self.__make_request('append', key_chain=key_chain, value=value, config_name=config_name)


if __name__ == "__main__":
    config_name = 'deploy_config_test'
    config_client = ConfigClient(config_name)
    
    # get
    config = config_client.get([])
    print("TEST: get\nresult: {}\n".format(json.dumps(config, indent=4)))

    # additem
    config_client.additem([],{'additem': 123})
    config = config_client.get([])
    print("TEST: additem\nresult: {}\n".format(json.dumps(config, indent=4)))

    # update
    config_client.update(['additem'], {'abc': 'hahahah'})
    config = config_client.get([])
    print("TEST: update\nresult: {}\n".format(json.dumps(config, indent=4)))

    # append
    config_client.update(['additem'], [{'1': '111', '2':'222'}])
    config_client.append(['additem'], {'3': '333'})
    config = config_client.get([])
    print("TEST: append\nresult: {}\n".format(json.dumps(config, indent=4)))

    # additem in list
    config_client.additem(['additem', 1], {'4': '444'})
    config = config_client.get([])
    print("TEST: add one item in dict in list\nresult: {}\n".format(json.dumps(config, indent=4)))

    # remove
    config_client.remove(['additem', 0, '2'])
    config = config_client.get([])
    print("TEST: remove\nresult: {}\n".format(json.dumps(config, indent=4)))

    # remove
    config_client.remove(['additem'])
    config = config_client.get([])
    print("TEST: remove\nresult: {}\n".format(json.dumps(config, indent=4)))
    