# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.abspath('.'))
import argparse
import traceback
import datetime
import time
import json, random
import tornado.web
from loguru import logger
from tools.helper.response_helper import MyResponse


if False:
    from deploy_nodes.helper.response_helper import MyResponse

def require(condition: bool, error: str):
    if not condition:
        raise Exception(error)

class ConfigHandler(tornado.web.RequestHandler):

    def __init__(self, *args, **kwargs):
        self.__selector = {
            'additem': self.__additem,
            'remove': self.__remove,
            'update': self.__update,
            'append': self.__append,
            'create': self.__create
        }
        super().__init__(*args, **kwargs) # 这里是必须要有的，否额 RequestHandler 类没有初始化，而且必须要有 *args 和 **kwargs

    def initialize(self, args):
        self.args = args
        self.config_path = self.args.config_path
    
    def __load_config(self, config_name) -> dict:
        config_file = os.path.join(self.config_path, "{}.json".format(config_name))
        if not os.path.exists(config_file):
            raise Exception("{} not exists".format(config_name))
        return json.load(
            open(
                config_file, 
                'r'
            )
        )
    
    def __has_config(self, config_name) -> bool:
        config_file = os.path.join(self.config_path, "{}.json".format(config_name))
        return os.path.exists(config_file)

    def __remove(self, *args, **kwargs):
        keys = json.loads(self.get_argument('key_chain'))
        require(isinstance(keys, list), "key_chain should be a list")
        config_name = self.get_argument('config_name')
        config = self.__load_config(config_name)
        ori_config = config
        if len(keys) == 0:
            # 直接删除整个json
            self.__save_config({}, config_name)
            return config
        for key in keys[0:-1]:
            if isinstance(config, list):
                key = int(key)
            config = config[key]
        lastkey = keys[-1]
        if isinstance(config, list):
            lastkey = int(lastkey)
            value = config[lastkey]
            del config[lastkey]
        else:
            value = config.pop(lastkey)
        self.__save_config(ori_config, config_name)
        return value

    def __update(self, *args, **kwargs):
        keys = json.loads(self.get_argument('key_chain'))
        require(isinstance(keys, list), "key_chain should be a list")
        value = json.loads(self.get_argument('value'))
        config_name = self.get_argument('config_name')
        config = self.__load_config(config_name)
        ori_config = config
        for key in keys[0:-1]:
            if isinstance(config, list):
                key = int(key)
            config = config[key]
        lastkey = keys[-1]
        if isinstance(config, list):
            lastkey = int(lastkey)
        config[lastkey] = value
        self.__save_config(ori_config, config_name)
        return ""

    def __additem(self, *args, **kwargs):
        keys = json.loads(self.get_argument('key_chain'))
        require(isinstance(keys, list), "key_chain should be a list")
        value = json.loads(self.get_argument('value'))
        config_name = self.get_argument('config_name')
        config = self.__load_config(config_name)
        ori_config = config
        for key in keys:
            if isinstance(config, list):
                key = int(key)
            config = config[key]
        config.update(value)
        self.__save_config(ori_config, config_name)
        return ""

    def __append(self, *args, **kwargs):
        keys = json.loads(self.get_argument('key_chain'))
        require(isinstance(keys, list), "key_chain should be a list")
        value = json.loads(self.get_argument('value'))
        config_name = self.get_argument('config_name')
        config = self.__load_config(config_name)
        ori_config = config
        for key in keys:
            if isinstance(config, list):
                key = int(key)
            config = config[key]
        require(isinstance(config, list), "can not append value to an object which is not a list")
        config.append(value)
        self.__save_config(ori_config, config_name)
        return ""

    def __create(self, *args, **kwargs):
        value = json.loads(self.get_argument('value'))
        config_name = self.get_argument('config_name')
        require(not self.__has_config(config_name), f"config_name({config_name}) exists")        
        self.__save_config(value, config_name)
    
    def __get(self, *args, **kwargs):
        keys = json.loads(self.get_argument('key_chain'))
        require(isinstance(keys, list), "key_chain should be a list")
        config_name = self.get_argument('config_name')
        config = self.__load_config(config_name)
        for key in keys:
            if isinstance(config, list):
                key = int(key)
            config = config[key]
        return config

    def __save_config(self, config, config_name):
        json.dump(
            config, 
            open(
                os.path.join(
                    self.config_path, 
                    '{}.json'.format(config_name)
                ), 
                'w'
            ),
            indent=4
        )

    def get(self):
        resp = MyResponse()
        try:
            resp.msg = self.__get()
        except Exception as e:
            resp.code = 101
            resp.error = str(e)
            logger.error(traceback.format_exc())
        finally:
            self.write(resp.as_dict())

    def post(self):
        resp = MyResponse()
        try:
            method = self.get_argument('method')
            func = self.__selector.get(method, None)
            require(func, "method is invalid. it must be in [set, update, append, create]")
            resp.msg = func()
        except Exception as e:
            resp.code = 101
            resp.error = str(e)
            logger.error(traceback.format_exc())
        finally:
            self.write(resp.as_dict())


def make_app(args):
    return tornado.web.Application([
        (r"/config", ConfigHandler, dict(args=args)),
    ])

def getArg():
    parser = argparse.ArgumentParser(description='params for python')
    parser.add_argument('--port', type=int, default=10051)
    parser.add_argument('--start_num', type=int, default=1)
    parser.add_argument('--config_path', type=str, default='./config_db')
    return parser.parse_args()

if __name__ == "__main__":
    args = getArg()
    if not os.path.exists(args.config_path):
        os.makedirs(args.config_path)
    logger.add("config_server.log")
    try:
        logger.info("server starting...")
        app = make_app(args)
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.bind(args.port)
        http_server.start(args.start_num)
        tornado.ioloop.IOLoop.instance().start()
        time.sleep(1)
    except Exception as e:
        logger.error(traceback.format_exc())
