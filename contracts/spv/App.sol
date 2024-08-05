pragma solidity ^0.8.0;

contract App {
    mapping(uint256 => bytes32) storeQueue;
    mapping(bytes32 => bytes32) crossMessage;

    function setMessage(bytes32 key, bytes32 value) public {
        crossMessage[key] = value;
    }

    function getPostion(bytes32 key) public pure returns(bytes32) {
        // keccak256(abi.encode(_key, balancesMappingIndex));
        return keccak256(abi.encode(key, 1));
    }

    function setQueue(uint256 n, bytes memory data) public{
        storeQueue[n] = keccak256(data);
    }

    function GetStorageLocation(uint256 key)
        public
        pure
        returns(uint256)
    {
        return uint256(keccak256(abi.encode(uint256(key), 0)));
    }



    
}