// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;
import "bcr/contracts/UpdateInterface.sol";

contract UpdateByLeaves is UpdateInterface {
    uint256 number;
    mapping(uint256 => bytes32) roots;
    mapping(uint256 => mapping(uint256 => uint256)) hashNum;
    mapping(uint256 => bytes32[]) trees;

    function build(uint256 idx, bytes memory data) external {
        bytes32 tempnode = keccak256(data);
        trees[idx].push(tempnode);
        uint256 length = trees[idx].length;
        bytes32[] memory nodes = trees[idx];
        while (length > 1) {
            for (uint i = 0; i < length; i += 2) {
                bytes32 leftnode = nodes[i];
                bytes32 rightnode;
                if (i != length - 1) {
                    rightnode = nodes[i + 1];
                } else {
                    rightnode = leftnode;
                }
                nodes[i / 2] = keccak256(abi.encodePacked(leftnode, rightnode));
            }
            length = (length + 1) / 2;
        }
        roots[idx] = nodes[0];
        hashNum[idx][trees[idx].length] = 1;
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
        return hashNum[idx][index];
    }
}
