import sys, os
sys.path.insert(0, os.path.abspath("."))
import hashlib
import math
from typing import List, Optional, Dict
from web3 import Web3
from eth_abi import encode

keccak = lambda x,y: Web3.solidity_keccak(abi_types=['bytes32', 'bytes32'], values=[x,y])
sha = lambda x: hashlib.sha256(str(x).encode()).hexdigest()
odd = lambda x: bool(x % 2)
ceillog = lambda x: 2 ** math.ceil(math.log(x, 2))

class MerkleBinaryTree:
    def __init__(self, hashes: List[bytes]) -> None:
        self.tree: Dict[int, List[bytes]] = {}
        if len(hashes) != 0:
            self.tree[0] = hashes
        else:
            self.tree[0] = [bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000000')]

    def build(self):
        self.__build(0)

    def __build(self, layerid: int):
        length = len(self.tree[layerid])
        if length == 1: return
        if length == 0: return
        uplayer: List[bytes] = []
        for i in range(0,length,2):
            leftnode = self.tree[layerid][i]
            rightnode = leftnode
            if i+1 < length:
                rightnode = self.tree[layerid][i+1]
            uplayer.append(keccak(leftnode, rightnode))
        layerid += 1
        self.tree[layerid] = uplayer
        self.__build(layerid)

    def get_root(self) -> bytes:
        return self.tree[len(self.tree)-1][0]

    def get_proof(self, index: int) -> List[bytes]:
        layerid = 0
        paths: List[bytes] = []
        while True:
            layer = self.tree[layerid]
            length = len(layer)
            if length == 1: break
            if index%2 == 0:
                sible = layer[index+1] if index+1 < length else layer[index]
            else:
                sible = layer[index-1]
            paths.append(bytes(sible))
            layerid += 1
            index //= 2
        return paths
    
    def verify(self, index: int, proof: List[bytes]) -> bool:
        layerid = 0
        node = self.tree[layerid][index]
        for sible in proof:
            if index % 2 == 1:
                node = keccak(sible, node)
            else:
                node = keccak(node, sible)
            index //=  2
            print(node.hex())
        print(self.get_root())
        return node == self.get_root()

def test(cmHashes, bcr):
    cmHashes = [bytes.fromhex(cmHash) for cmHash in cmHashes]
    bcr = bytes.fromhex(bcr)

    mbt = MerkleBinaryTree(hashes=cmHashes)
    mbt.build()
    root = mbt.get_root()
    print(root)
    print(root == bcr)

    for i in reversed(range(len(mbt.tree))):
        layer = mbt.tree[i]
        print(f"{i}: ", end='')
        for j in range(len(layer)):
            print(layer[j].hex(), end=', ')
        print()

    for i in range(len(cmHashes)):
        print(f"index: {i}")
        proof = mbt.get_proof(index=i)
        print([node.hex() for node in proof])
        assert mbt.verify(i, proof)


if __name__ == "__main__":
    cmHashes = ['34c35189d67b46ee346c7c335008ee208963fb52beef4e2753d1d652e6edc921', '0e56f9ab913cef252331a05014817348a5555ab9709755cee5e57993fe9c52f1', '65e98acfdc354f3e941149582152b17c93214733e16919515997122dec2ab0da', 'abf74666b56d7090f1642ece937ded5b99da767f71e38f815010a035ed8c3132']
    bcr = '350117442d7ecc25611ffff8e7fdc761508c5e7042c5cc89bbf4fcf8574cf4d2'
    test(cmHashes, bcr)

    cmHashes = ['8968ad1e54db2c6a3f0d37330666cc79dd21de1d169d6d24118607dd0dccc82b', '8211e883c047bac07e4fb976bcf36c30b5fcb273896543927d4aa454839e15ba', '965f3aaa3b156edd2fb986d1cd2596568798a5ae8388c503eeb0d21b805f25ac', 'd3abbfa9b48f93781fa62fa814482ca1176a7638bb66c72be7699dca30f7c526', 'af28bdb84155d9330dc8bffe11cba30d06ee819eeb76624f35a604782d6db87e']
    bcr = 'd25f6236f30838526300d0d91dbd48ee5e9cc5bfcdd15e2e96d626681c44c0a6'
    test(cmHashes, bcr)

    cmHashes = ['8968ad1e54db2c6a3f0d37330666cc79dd21de1d169d6d24118607dd0dccc82b']
    bcr = '8968ad1e54db2c6a3f0d37330666cc79dd21de1d169d6d24118607dd0dccc82b'
    test(cmHashes, bcr)

    cmHashes = []
    bcr = '0000000000000000000000000000000000000000000000000000000000000000'
    test(cmHashes, bcr)
    
    

    
    