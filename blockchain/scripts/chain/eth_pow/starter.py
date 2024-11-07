import os, sys
sys.path.insert(0, os.path.abspath('.'))
import shutil

# if os.path.abspath('.') == '/':
from scripts import utils
from scripts import setting

def chain_init(geth, datadir, logdir_init, genesis):
    cmd_init = '{geth} --datadir {datadir} init {genesis} > {logdir} 2>&1'.format(
        geth=geth, datadir=datadir, genesis=genesis, logdir=logdir_init
    )
    _ = utils.exec_command(cmd_init, cmd_type='chain init')

def chain_start(geth, datadir, logdir_start, bootnode, other_args):
    rpcport, port = utils.get_random_free_port(setting.PORTS_RANGE, n=2)
    extip = os.environ['HOSTIP'] # set env HOSTIP when running docker container
    cmd_start = '''nohup \
{geth} \
--rpc \
--rpcaddr 0.0.0.0 \
--rpcport {rpcport} \
--rpccorsdomain "*" \
--datadir {datadir} \
--port {port} \
--bootnodes "{bootnode}" \
--nat extip:{extip} \
--syncmode "full" \
{other_args} \
> {logdir} \
2>&1 & '''.format(
    geth=geth,
    rpcport=rpcport,  
    datadir=datadir,
    port=port,
    bootnode=bootnode,
    extip=extip,
    other_args=other_args,
    logdir=logdir_start
)
    _ = utils.exec_command(cmd_start, cmd_type='start chain')
    pids = utils.get_pid_by_condition(geth, rpcport, port, datadir)
    utils.require(len(pids) <= 1, "find too many process pids, cmd: {}".format(cmd_start))
    utils.require(len(pids) != 0, "chain start failed, find no process pid! cmd: {}".format(cmd_start))
    return pids[0], rpcport    

def stop(idx: str):
    # TODO
    # 创建关闭指令 
    piddir = os.path.join(setting.CACHE_PID, idx)
    utils.killlast(piddir)
    child = os.path.join(setting.ROOT_DIR, idx)
    if os.path.exists(child):
        shutil.rmtree(child)

def start(idx: str, chain_config: dict):
    """启动区块链
    idx: 链标识
    **kwargs: 
        - bootnode: eth的bootnode
        - genesis_config: 创世区块文件
        - account_files: 需要初始化的账户
    """
    # 先停止之前的chain
    stop(idx)
    bootnode = chain_config['bootnode']
    genesis_config = chain_config['genesis_config']
    account_files = chain_config['account_files']
    geth_cc = os.path.join(setting.BIN_DIR, 'geth_1.10.0')
    piddir = os.path.join(setting.CACHE_PID, idx)
    child = os.path.join(setting.ROOT_DIR, idx)
    os.makedirs(child)
    datadir = os.path.join(child, 'data')
    os.makedirs(datadir)
    genesis = utils.write_genesis(datadir, genesis_config)
    utils.write_account(datadir, account_files)
    # genesis_account = utils.generate_account(geth_hit, datadir)
    # utils.generate_genesis_pow(genesis, genesis_account)
    logdir_init = os.path.join(child, 'init.log')
    logdir_start = os.path.join(child, 'start.log')
    # 以太坊需要初始化区块链
    chain_init(geth_cc, datadir, logdir_init, genesis)
    # 启动区块链
    other_args = "--rpcapi 'personal,eth,net,web3,miner,txpool,admin' --allow-insecure-unlock"
    pid, rpcport = chain_start(geth_cc, datadir, logdir_start, bootnode, other_args)
    utils.writepid(piddir, pid)
    return rpcport

    

    