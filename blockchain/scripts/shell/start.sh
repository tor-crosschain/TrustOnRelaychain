../bin/geth_hit \
--targetgaslimit 4294967295 \
--rpc \
--rpcaddr 0.0.0.0 \
--rpcport 60010 \
--rpcapi "personal,eth,net,web3,miner,txpool,admin,clique" \
--rpccorsdomain "*" \
--datadir ./data \
--port 60020 \
--bootnodes "enode://84eb2cfdda7df92f4289a7f1d7e90e38ae6ee3cbe3ebe5b873d0030768f9293389888c55822810d68f28f7272b62de3d794c7a9a87b6ad31e17167118a341fc0@10.21.162.162:60000" \
--nat extip:10.21.4.34
--syncmode "full" \
console
