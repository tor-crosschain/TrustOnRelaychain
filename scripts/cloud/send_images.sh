#!/bin/bash
# 
# pre-operation
# docker save 10.21.4.204:5000/yiiguo/u16py | gzip > u16py.tar.gz

ips=(122.9.39.32 114.116.221.190 122.9.33.196 114.116.215.14)
# ips=("122.9.45.233")
for ip in ${ips[@]}
do
echo "send to $ip......"
scp /home/yiiguo/installer/docker_images/u16py_latest.tar.gz root@$ip:/root/
# scp /home/yiiguo/installer/docker_images/sgx_latest.tar.gz root@$ip:/root/
echo "finish!"
done