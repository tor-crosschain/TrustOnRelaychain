import pymongo
import time
from typing import Union

def format_time():
    return time.strftime("%Y-%m-%d %HH:%MM:%SS", time.localtime(time.time()))

class RespHelper(object):
    def __init__(self, host:str ="localhost", port: int=27017, db="respdb", table="resp"):
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

    
    def insert(self, cmdid: str, resp: str) -> str:
        result = self.collection.update_one(
            {
                'cmdid': cmdid,
            },
            {
                '$set': {
                    'resp': resp,
                    'createtime': format_time()
                }
            },
            upsert=True
        )
        return str(result.upserted_id)
    
    def getresp(self, cmdid: str):
        result = self.collection.find(
            {'cmdid': cmdid},
            sort=[('createtime', pymongo.ASCENDING)]
        )
        if result: return result[0]
        return {}
        
