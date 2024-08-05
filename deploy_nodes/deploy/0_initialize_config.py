"""
初始化所有的config文件
"""
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from tools.helper.exception_helper import require

init_config_dir = './deploy_nodes/init_config'
config_db_dir = './config_db'
require(os.path.exists(init_config_dir), "{} not exists!".format(init_config_dir))
require(os.path.exists(config_db_dir), "{} not exists!".format(config_db_dir))

os.system('rm {config_db_files} -f  && cp {init_config_files} {config_db_dir} && chmod 775 {config_db_dir} && chmod 666 {config_db_files}'.format(
    config_db_files=os.path.join(config_db_dir, '*'),
    init_config_files=os.path.join(init_config_dir, '*'),
    config_db_dir=config_db_dir
))
