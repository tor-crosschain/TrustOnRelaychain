# ToR
## Setup
### Start dockers
1. 下载镜像
```
docker pull 10.21.4.204:5000/yiiguo/u16py
```
2. 启动容器

操作的执行过程都在docker容器里面，docker容器把所有的环境都已经设置好了。

具体的启动过程在`docker-scripts/deploy/run.sh`里面，几个参数解释如下:
- "ssh_port": 指定ssh的端口号，如果默认的端口号(60022)和你的宿主机其他的端口号冲突了，那就换一个；
- "-v": 路径映射。可以删除，只要容器里面有该项目即可；如果不删除，那就把前半部分的路径修改为宿主机上的项目路径；
- "--name": 容器的名称。随便修改，自己记住就行，如果修改了，那么 `docker-scripts/deploy/exec.sh` 和 `docker-scripts/deploy/rm.sh` 中的容器名称也要做相应的修改
- "10.21.4.204:5000/yiiguo/u16py": 容器的镜像名称。如果在所里，应该可以直接获取到这个镜像，只要能ping通10.21.4.24地址就可以用，否则需要宿主机上有镜像的安装包。

```bash
# 启动容器，执行一次就行
sh docker-scripts/deploy/run.sh
# 进入容器，用的最多的命令
sh docker-scripts/deploy/exec.sh
# 删除容器，不需要该容器的时候可以删除掉
# sh docker-scripts/deploy/rm.sh
```

进入容器后，需要首先更换 python eth_account 工具包下面的两个文件
```bash
sh special/path
```

## 配置jsonDB服务

以下操作需要在容器内执行，在项目根目录下执行。

1. 启动jsonDB服务器
- "--port 10051": 可以省略，服务默认端口号是10051
- "--config_path ./config_db": 可以省略，服务默认的config数据库路径就是`./config_db`, 如果config_path不存在，那么需要手动创建
然后直接执行服务
```bash
python deploy_nodes/config_server/config_server.py --port 10051 --config_path ./config_db
# 上面的是直接前台运行，一旦推出shell，进程就会被杀掉，可以使用下面的命令在后台运行该服务
# nohup python deploy_nodes/config_server/config_server.py --port 10051 --config_path ./config_db 2>&1 >config_server.log &
```
2. 设置 `setting.py`
'''python
CONFIG_DB_HOST = '127.0.0.1' # jsonDB服务器的IP地址
CONFIG_DB_PORT = 10051 # jsonDB服务器的端口号
'''

## 部署区块链

### 启动区块链节点容器
为了方便环境的设置，我们的各个区块链节点都是在提前配置好的docker容器里面运行，所以需要在运行项目的区块链节点宿主机上启动docker容器，容器的镜像可以通过如下方式获得:
```bash
docker pull 10.21.4.204:5000/yiiguo/u16py # 其实和项目运行的环境镜像是一个，但是后面的启动方式不同，主要是为了方便区块链节点的运行
```
比如，你现在有一台区块链节点宿主机（比如实验室的10.21.4.34服务器），那么你需要通过上面的方式先获取镜像，然后执行下面的命令启动容器:
```bash
#####################
# ip: 设置成你的区块链节点宿主机的ip，比如10.21.4.34，下面的这种自动获取自动匹配的方式只适合在实验室环境下使用，其他环境下（比如云服务或者你自己的电脑）则需要手动设置
# sshport: 指定容器的ssh端口号，默认是60022，容器启动之后，可以通过该端口进行ssh连接。
#
# docker 参数解释:
# "-p": 端口映射，宿主机端口号范围:容器端口号范围/端口类型。下面设置了两个端口映射，一个是TCP，一个是UDP，UDP主要是为了区块链的bootnode程序，bootnode程序监听的是UDP端口；宿主机如果设置了防火墙，则需要打开对应的端口。
# "--name": 容器的名称。
# "10.21.4.204:5000/yiiguo/u16py": 镜像的名称。
#####################
ip=`ifconfig -a|grep inet|grep -v 127.0.0.1|grep 'broadcast 10.21.255.255'|grep -v inet6|awk '{print $2}'|tr -d "addr:"​`
# ip=10.21.4.34
sshport=60022
if [ ! -z $1 ]; then
    sshport=$1
fi
docker run -itd --env COLUMNS=800 --env LINES=100  -p 61000-61050:61000-61050/tcp -p 61000-61050:61000-61050/udp  --name test_crosschain 10.21.4.204:5000/yiiguo/u16py bash -c "\
echo HOSTIP=$ip >> /etc/environment && \
/scripts/start_ssh.sh $sshport \
"
```

### jsonDB信息

为了方便使用jsonDB，也为了方便测试，我们先创建了一个文件夹 `deploy_nodes/init_config`，这里面放置了所有jsonDB的初始文件，项目需要重启进行测试的时候需要将这些jsonDB初始文件复制到jsonDB服务器启动时指定的`--config_path ./config_db`路径下，之后jsonDB的操作都以`./config_db`路径下的这些jsonDB初始文件为基础。

`deploy_nodes/init_config` 路径下的jsonDB初始文件，主要包括以下文件：
1. server.json 

填写所有需要用到的区块链节点信息（包括治理链、平行链、互联链的所有节点）。程序会通过`ssh`的原理把项目所需的文件（包括geth程序，bootnode程序等等）发送到这些区块链节点上。
```json
[
    {
        "host": "127.0.0.1", //区块链节点宿主机的ip地址，不是区块链节点容器的ip，如果你在实验室的10.21.4.34服务器上部署的区块链节点容器，那么这里的host就是10.21.4.34
        "port": "60022", // 区块链节点宿主机与区块链节点容器映射的ssh端口。因为在启动区块链节点容器的脚本中，设置了端口映射，所以通过该区块链节点宿主机端口，可以直接ssh到区块链节点容器。
        "username": "root", // 区块链节点容器的ssh用户名
        "password": "ttfgCbowIy14eZay", // 区块链节点容器的ssh密码
        "send": true // 是否需要发送项目文件。因为在测试过程中，很多时候不需要每次都发送项目文件，所以在发送一次之后可以手动设置为 false
    }
]
```

2. transfer.json 

填写文件传输所需要的路径。
```json
{
    "local_files": "./blockchain", // 本地需要压缩打包的文件夹路径
    "local_tar": "./deploy_nodes/deploy/blockchain.tar", // 打包之后待发送的文件路径
    "remote_tar": "/root/workspace/blockchain.tar", // 发送到区块链节点容器的目的文件路径
    "remote_files": "/root/workspace/blockchain", // 区块链节点容器中目的文件解压后的路径
    "cache_pid_dir": "/root/workspace/cache_pid" // 区块链节点容器中程序的进程id，主要用于kill远程进程
}
```

3. parallel_chain.json

填写所有的平行链信息。随着脚本的执行，会填充更多的新字段。


### 程序执行流程

```bash
# 初始化jsonDB数据库，其实就是将init_config文件夹下的json文件复制到config_db目录下
python deploy_nodes/deploy/initialize_config.py
python deploy_nodes/deploy/0_gzip.py
python deploy_nodes/deploy/1_send_tar.py

python relayer/aor/generate_configs.py --paranum 3
# get the output which is the config name (for example: blockchains_aor_3)

# start chains with the same config name (for example: blockchains_aor_3)
python deploy_nodes/deploy/4_0_start_parallel_chain.py --config_name blockchains_aor_3

# deploy contracts with the same config name (for example: blockchains_aor_3)
python contracts/deploy.py --config_name blockchains_aor_3

# start all gateways with the same config name (for example: blockchains_aor_3)
python relayer/aor/scheduler.py --config_name blockchains_aor_3

# stop all chains with the same config name (for example: blockchains_aor_3)
python deploy_nodes/deploy/stop_remote_geth.py --config_name blockchains_aor_3
```