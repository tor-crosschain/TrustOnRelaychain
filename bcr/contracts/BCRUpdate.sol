// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;
import "bcr/contracts/UpdateInterface.sol";

contract BCRUpdate is UpdateInterface {
    uint256 number;
    bytes32 myhash;
    mapping(uint256 => bytes32) roots;
    mapping(uint256 => bytes32[]) trees;
    mapping(uint256 => uint32) xmcnts;

    function build(uint256 idx, bytes memory data) external {
        bytes32 tempnode = keccak256(data);
        xmcnts[idx] += 1;

        uint32 index = xmcnts[idx];
        bytes32[] memory path = trees[idx];
        bytes32[] memory nextpaths = new bytes32[](index);
        uint32 point_nextpaths = 0;
        uint8 flag = 2;
        uint32 pathpoint = 0;
        while (index >= 1) {
            if (index == 1) {
                roots[idx] = tempnode;
                nextpaths[point_nextpaths++] = tempnode;
                break;
            }
            if (index % 2 == 1) {
                if (flag == 2 || flag == 0) {
                    nextpaths[point_nextpaths++] = tempnode;
                }
                tempnode = keccak256(abi.encodePacked(tempnode, tempnode));
                flag = 1;
                index = index / 2 + (index % 2);
            } else {
                bytes32 node = path[pathpoint];
                pathpoint += 1;
                if (flag == 1) {
                    nextpaths[point_nextpaths++] = node;
                } else if (flag == 2) {
                    flag = 0;
                }
                tempnode = keccak256(abi.encodePacked(node, tempnode));
                index = index / 2 + (index % 2);
            }
        }
        delete trees[idx];
        trees[idx] = new bytes32[](point_nextpaths);
        for (uint32 i = 0; i < point_nextpaths; i++) {
            trees[idx][i] = nextpaths[i];
        }
    }

    function retrieve(uint256 idx) public view returns (bytes32[] memory) {
        return trees[idx];
    }

    function retrieveRoot(uint256 idx) external view returns (bytes32) {
        return roots[idx];
    }

    function queryHashNum(
        uint256 idx,
        uint256 index
    ) external view returns (uint256) {
        return 0;
    }
}
