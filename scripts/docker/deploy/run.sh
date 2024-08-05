ssh_port=60022
docker run -itd --env COLUMNS=800 --env LINES=100 -p 10051:10051  -v $(pwd):/root/workspace/crosschain_dev  --name test_deployall 10.21.4.204:5000/yiiguo/u16py bash -c "/scripts/start_ssh.sh $ssh_port"
