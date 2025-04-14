// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.2 <0.9.0;

import "bcr/contracts/lib.sol";
import "bcr/contracts/UpdateInterface.sol";

contract Cross {
    struct Payload {
        address sourceApp;
        address targetApp;
        bytes sourceFunc;
        bytes targetFunc;
        bytes targetData;
    }

    struct CrossMessage {
        uint sourceChain;
        uint targetChain;
        uint sourceValue;
        uint targetValue;
        address sourceUser;
        address targetUser;
        Payload payload;
    }

    CrossMessage[] cms;
    mapping(bytes32 => uint) cmHashes;

    address updateAlg = address(0);

    function setUpdateAlg(address _addr) public {
        updateAlg = _addr;
    }

    function crossTransfer(
        uint sourceChain,
        uint targetChain,
        uint sourceValue,
        uint targetValue,
        address targetUser,
        address sourceApp,
        address targetApp,
        bytes memory sourceFunc,
        bytes memory targetFunc,
        bytes memory targetData,
        uint256 treeidx
    ) public payable {
        address sourceUser = msg.sender;
        Payload memory payload = Payload(
            sourceApp,
            targetApp,
            sourceFunc,
            targetFunc,
            targetData
        );
        CrossMessage memory cm = CrossMessage(
            sourceChain,
            targetChain,
            sourceValue,
            targetValue,
            sourceUser,
            targetUser,
            payload
        );

        cms.push(cm);
        bytes32 cmhash = hashCM(cm);
        cmHashes[cmhash] = cms.length - 1;

        UpdateInterface(updateAlg).build(treeidx, cmToBytes(cm));
    }

    function cmToBytes(
        CrossMessage memory cm
    ) public pure returns (bytes memory x) {
        x = abi.encodePacked(
            Utils.uint256ToBytes(cm.sourceChain),
            Utils.uint256ToBytes(cm.targetChain),
            Utils.uint256ToBytes(cm.sourceValue),
            Utils.uint256ToBytes(cm.targetValue),
            Utils.addressToBytes(cm.sourceUser),
            Utils.addressToBytes(cm.targetUser),
            Utils.addressToBytes(cm.payload.sourceApp),
            Utils.addressToBytes(cm.payload.targetApp),
            cm.payload.sourceFunc,
            cm.payload.targetFunc,
            cm.payload.targetData
        );
    }

    function hashCM(CrossMessage memory cm) public pure returns (bytes32 x) {
        x = keccak256(cmToBytes(cm));
    }

    function queryHashNum(uint256 idx, uint256 index) external view returns (uint256) {
        return UpdateInterface(updateAlg).queryHashNum(idx, index);
    }
}
