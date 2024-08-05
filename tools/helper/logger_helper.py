import os, sys
import requests
import setting
import socket
from loguru import logger
from datetime import datetime
from tools.helper.response_helper import MyResponse
from tools.helper.exception_helper import require
from tools.helper.utils_helper import get_host_ip

def _send_log(msg):
    """
    level = self.get("level")
    host = self.get("host")
    file = self.get("file")
    function = self.get("function")
    line = self.get("line")
    msg = self.get("msg")
    logtime = self.get("logtime")
    """
    record = msg.record
    level_name = record['level'].name
    if level_name in setting.LOG_REMOTE_LEVELS.keys():
        logtime = datetime.strftime(record['time'], "%Y-%m-%d %H:%M:%H")
        error = None
        for i in range(3):
            try:
                # curl http://10.21.162.162:10051/log -d 'level=info&host=10.21.162.162&file=test&function=none&line=15&msg=hellotest&logtim=10101010'
                data = {
                    "level": level_name,
                    "host": get_host_ip(),
                    "file": record['file'].name,
                    "function": record['function'],
                    "line": record['line'],
                    "msg": record['message'],
                    "logtime": logtime
                }
                url = setting.LOCAL_SERVER_URL_LOG
                r = requests.post(
                    url=url,
                    data = data
                )
                require(r.status_code == 200, "log server status_code wrong, status_code: {}".format(r.status_code))
                resp = MyResponse(r.json())
                require(resp.code == 0, "log server return failed! resp: {}".format(resp.as_str()))
                return
            except Exception as e:
                error = str(e)
        send_failed_file = setting.LOG_REMOTE_FAILED_FILE + "_{}_{}".format(os.path.basename(sys.argv[0]).split('.')[0], os.getpid())
        with open(send_failed_file, 'a') as f:
            f.write("send log failed! error: {}, data: {}\n".format(error, data))
    

def _add_remote_level():
    for key in setting.LOG_REMOTE_LEVELS:
        logger.level(
            name=key,
            no=setting.LOG_REMOTE_LEVELS[key]['no'],
        )

def _init_remote_failed_file():
    if os.path.exists(setting.LOG_REMOTE_FAILED_FILE):
        os.remove(setting.LOG_REMOTE_FAILED_FILE)
    dirname = os.path.abspath(os.path.dirname(setting.LOG_REMOTE_FAILED_FILE))
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def init_logger(filename='log/unknown.log'):
    _init_remote_failed_file()
    _add_remote_level()
    logger.add(_send_log)
    logger.add(filename)
