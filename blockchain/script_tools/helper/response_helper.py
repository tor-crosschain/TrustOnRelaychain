# encoding: utf-8
import json
class MyResponse(object):

    def __init__(self, *args, **kwargs):
        args_length = len(args)
        if args_length == 1:
            self.__init_by_dict(*args)
            return
        elif args_length == 3:
            self.__init_by_key(*args)
            return
        
        kwargs_length = len(kwargs)
        if kwargs_length in [0, 1, 2, 3]:
            self.__init_by_key(**kwargs)
            return
        raise Exception("unknown args and kwargs")
        

    def __init_by_key(self, code=0, msg="", error=""):
        self.code = code
        self.msg = msg
        self.error = error
    
    def __init_by_dict(self, response: dict):
        self.code = response['code']
        self.msg = response['msg']
        self.error = response['error']

    def as_dict(self) -> dict:
        return {
            'code': self.code,
            'msg': self.msg,
            'error': self.error
        }
    def as_str(self) -> str:
        return json.dumps(self.as_dict())