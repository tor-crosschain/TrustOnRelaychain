// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;
import "bcr/contracts/UpdateInterface.sol";

contract UpdateByTree is UpdateInterface {
    uint256 number;

    mapping(uint256 => mapping(uint256 => mapping(uint256 => bytes32))) trees; // idx -> layer(1) -> index(1) : bytes32
    mapping(uint256 => uint256) leaveslength;
    mapping(uint256 => uint256) layernumber;
    mapping(uint256 => mapping(uint256 => uint256)) hashNum;

    function build(uint256 idx, bytes memory data) external {
        bytes32 value = keccak256(data);
        uint256 layeridx = 1;
        leaveslength[idx] += 1;
        uint256 templength = leaveslength[idx];
        trees[idx][layeridx][templength] = value;
        hashNum[idx][leaveslength[idx]] = 0;
        while (templength > 1) {
            bytes32 left = trees[idx][layeridx][templength - 1];
            bytes32 right = left;
            if (templength % 2 == 0) {
                left = trees[idx][layeridx][templength - 1];
                right = trees[idx][layeridx][templength];
            } else {
                left = trees[idx][layeridx][templength];
                right = left;
            }
            if (layeridx > 1) {
                hashNum[idx][leaveslength[idx]] += templength;
            }
            templength = (templength - 1) / 2 + 1;
            layeridx += 1;
            bytes32 parent = keccak256(abi.encodePacked(left, right));
            trees[idx][layeridx][templength] = parent;
        }
        layernumber[idx] = layeridx;
    }

    // function retrieve(uint32 idx) public view returns (bytes32){
    //     return trees[idx][layernumber][1];
    // }

    function retrieveRoot(uint256 idx) external view returns (bytes32) {
        return trees[idx][layernumber[idx]][1];
    }

    function queryHashNum(
        uint256 idx,
        uint256 index
    ) external view returns (uint256) {
        return hashNum[idx][index];
    }
}
