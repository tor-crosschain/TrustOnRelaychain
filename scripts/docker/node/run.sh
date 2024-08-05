#!/bin/sh
ip=$(/usr/bin/hostname -I | awk '{print $1}')
echo $ip
# TODO add check IP
# ip=10.21.4.34
sshport=60022
if [ ! -z $1 ]; then
    sshport=$1
fi
docker run -itd --env COLUMNS=800 --env LINES=100  -p 60000-60100:60000-60100/tcp -p 60000-60100:60000-60100/udp  --name test_crosschain 10.21.4.204:5000/yiiguo/u16py bash -c "\
echo HOSTIP=$ip >> /etc/environment && \
/scripts/start_ssh.sh $sshport \
"