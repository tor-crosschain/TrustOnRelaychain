import pymongo
import time
from typing import Union

def format_time():
    return time.strftime("%Y-%m-%d %HH:%MM:%SS", time.localtime(time.time()))

class LogdbHelper(object):
    def __init__(self, host:str ="localhost", port: int=27017, db="logdb", table="log"):
        self.client = pymongo.MongoClient(host=host, port=port)
        
        # delete old log
        self.db = self.client[db]
        if table in self.db.collection_names(include_system_collections=False):
            try:
                self.db.drop_collection(table)
            except:
                # in case of multi processes drop the collection at the same time
                # tornado multi processes
                pass
        self.collection = self.db[table]

    
    def putlog(self, logid: int, level: str, host: str, _file: str, function: str, line: str, msg: str, logtime: str) -> str:
        '''
        logid=newid,
        level=level,
        host=host,
        file=_file,
        function=function,
        line=line,
        msg=msg,
        logtime=logtime
        '''
        result = self.collection.insert_one({
            'logid': logid,
            'level': level,
            'host': host, 
            'file': _file,
            'function': function,
            'line': line,
            'msg': msg,
            'logtime': logtime, # yyyy-mm-dd hh:mm:ss
            'createtime': format_time()
        })
        return str(result.inserted_id)
    
    def getlog(self, logid_last: int) -> Union[list, None]:
        return self.collection.find(
            {'logid': {'$gt': logid_last}},
            sort=[('logid', pymongo.ASCENDING)]
        )
