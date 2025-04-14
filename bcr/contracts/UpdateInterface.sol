// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

interface UpdateInterface {
    function build(uint256 idx, bytes memory data) external;
    function retrieveRoot(uint256 idx) external view returns (bytes32);
    function queryHashNum(uint256 idx, uint256 index) external view returns (uint256);
}
