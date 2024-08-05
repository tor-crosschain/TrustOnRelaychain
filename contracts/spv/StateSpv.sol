pragma solidity ^0.8.0;


import "./lib/StateProofVerifier.sol";
import "./lib/RLPReader.sol";
import "./lib/Utils.sol";


contract StateSpv {

    // =========================================== Application =========================================== 
    struct Payload {    
        address targetApp;
        bytes targetFunc;
        bytes targetData;
    }

    struct CrossMessage {
        uint sourceChain;
        uint targetChain;
        address targetUser;
        Payload payload;
    }
    
    mapping(uint256 => bytes32) cmHashes;
    mapping(uint256 => bytes32) roots; // BCR root
    mapping(uint256 => bytes32) cmHashesOnRelay;
    mapping(uint256 => mapping(uint256 => bytes32)) rootsOnRelay; // BCR stored on relay chain. chain_id => block_height => BCR 
    mapping(uint256 => mapping(uint256 => bytes32)) rootsOnDst; // bcr stored on the dst parallel chain. chain_id => block_height => BCR 
    
    CrossMessage[] cms;

    event CMIndex(
        uint256 index
    );
    event CMIndexOnRelay(
        uint256 index
    );
    
    function crossSend(
        uint sourceChain,
        uint targetChain,
        address targetUser,
        address targetApp,
        bytes memory targetFunc,
        bytes memory targetData
    ) public payable {
        Payload memory payload = Payload(
            targetApp,
            targetFunc,
            targetData
        );
        CrossMessage memory cm = CrossMessage(
            sourceChain,
            targetChain,
            targetUser,
            payload
        );

        cms.push(cm);
        bytes32 cmhash = hashCM(cm);
        uint cmIndex = cms.length - 1;
        cmHashes[cmIndex] = cmhash;
        // uint256 treeidx = block.number;
        // build(treeidx, cmToBytes(cm));
        emit CMIndex(cmIndex);
    }

    function crossSendToR(
        uint sourceChain,
        uint targetChain,
        address targetUser,
        address targetApp,
        bytes memory targetFunc,
        bytes memory targetData
    ) public payable {
        Payload memory payload = Payload(
            targetApp,
            targetFunc,
            targetData
        );
        CrossMessage memory cm = CrossMessage(
            sourceChain,
            targetChain,
            targetUser,
            payload
        );

        cms.push(cm);
        bytes32 cmhash = hashCM(cm);
        uint cmIndex = cms.length - 1;
        cmHashes[cmIndex] = cmhash;
        uint256 treeidx = block.number;
        build(treeidx, cmToBytes(cm));
        emit CMIndex(cmIndex);
    }

    struct CMBlock {    
        CrossMessage cm;
        uint256 height;
    }
    mapping(bytes32 => CrossMessage) cmsReceived;
    mapping(uint256 => CMBlock) cmsRecordByCount;

    uint countOnDst = 0;
    // used in AoR
    // the dst parachain receive from relay chain
    function crossReceiveFromRelay(
        CrossMessage memory cm, 
        bytes32 cmHash, 
        bytes32 position, 
        address sourceAddress, 
        uint256 sourceHeight,
        bytes memory accountProof,
        bytes memory storageProof

    ) public {
        bytes32 cmHashCalc = hashCM(cm);
        if (cmHashCalc != cmHash) {
            revert("cmhash not match!");
        }
        // uint256 chain_id = cm.sourceChain;
        bytes32 root = getStateRoot(0, sourceHeight);
        verify(position, sourceAddress, abi.encode(cmHash), root, accountProof, storageProof);
        cmsReceived[cmHashCalc] = cm;
        countOnDst += 1;
        CMBlock memory cmBlock = CMBlock(
            cm,
            block.number
        );
        cmsRecordByCount[countOnDst] = cmBlock;
    }

    // used in NoR
    // the dst parachain receive cm from the source parachain
    function crossReceiveFromPara(
        CrossMessage memory cm, 
        bytes32 cmHash, 
        bytes32 position, 
        address sourceAddress, 
        uint256 sourceHeight,
        bytes memory accountProof,
        bytes memory storageProof

    ) public {
        bytes32 cmHashCalc = hashCM(cm);
        if (cmHashCalc != cmHash) {
            revert("cmhash not match!");
        }
        // uint256 chain_id = cm.sourceChain;
        bytes32 root = getStateRoot(cm.sourceChain, sourceHeight);
        verify(position, sourceAddress, abi.encode(cmHash), root, accountProof, storageProof);
        cmsReceived[cmHashCalc] = cm;
        countOnDst += 1;

        CMBlock memory cmBlock = CMBlock(
            cm,
            block.number
        );
        cmsRecordByCount[countOnDst] = cmBlock;
    }

    // used in ToR
    // the dst parachain receive cm from source parachain
    function crossReceiveFromParaToR(
        CrossMessage memory cm, 
        bytes32 cmHash, 
        uint256 position, 
        uint256 sourceHeight,
        bytes32[] memory proof

    ) public {
        bytes32 cmHashCalc = hashCM(cm);
        if (cmHashCalc != cmHash) {
            revert("cmhash not match!");
        }
        // uint256 chain_id = cm.sourceChain;
        bytes32 bcr = rootsOnDst[cm.sourceChain][sourceHeight];
        verifyBCR(position, cmHash, bcr, proof);

        cmsReceived[cmHashCalc] = cm;
        countOnDst += 1;


        CMBlock memory cmBlock = CMBlock(
            cm,
            block.number
        );
        cmsRecordByCount[countOnDst] = cmBlock;
    }

    function crossReceiveBCR(
        uint256 source_chain_id,
        uint256 source_height,
        bytes32 bcr, 
        bytes32 position, 
        address relayAddress, 
        uint256 relayHeight,
        bytes memory accountProof,
        bytes memory storageProof
    ) public {
        bytes32 root = getStateRoot(0, relayHeight);
        verify(position, relayAddress, abi.encode(bcr), root, accountProof, storageProof);
        rootsOnDst[source_chain_id][source_height] = bcr;
    }

    function getCountOnDst() public view returns(uint256) {
        return countOnDst;
    }

    function getDstCMByCount(uint256 idx) public view returns(CMBlock memory){
        return cmsRecordByCount[idx];
    }

    function resetCountOnDst() public {
        countOnDst = 0;
    }

    // used in AoR
    // the relay chain receive cm from the source parachain
    mapping(bytes32 => CrossMessage) cmsReceivedOnRelay;
    uint count = 0;
    function crossReceiveOnRelay(
        CrossMessage memory cm, 
        bytes32 cmHash, 
        bytes32 position, 
        address sourceAddress, 
        uint256 sourceHeight,
        bytes memory accountProof,
        bytes memory storageProof

    ) public {
        bytes32 cmHashCalc = hashCM(cm);
        if (cmHashCalc != cmHash) {
            revert("cmhash not match!");
        }
        uint256 chain_id = cm.sourceChain;
        bytes32 root = getStateRoot(chain_id, sourceHeight);
        verify(position, sourceAddress, abi.encode(cmHash), root, accountProof, storageProof);
        cmsReceivedOnRelay[cmHashCalc] = cm;
        count += 1;
        cmHashesOnRelay[count] = cmHashCalc;
        emit CMIndexOnRelay(count);
    }

    function getCMHashByIndex(uint cmIndex) public view returns(bytes32){
        return cmHashes[cmIndex];
    }

    function getCMByIndex(uint cmIndex) public view returns(CrossMessage memory) {
        return cms[cmIndex];
    }

    function getCMHashByIndexOnRelay(uint cmIndex) public view returns(bytes32){
        return cmHashesOnRelay[cmIndex];
    }

    function getCMByHashOnRelay(bytes32 cmHash) public view returns(CrossMessage memory) {
        return cmsReceivedOnRelay[cmHash];
    }

    function cmToBytes(
        CrossMessage memory cm
    ) public pure returns (bytes memory x) {
        x = abi.encodePacked(
            Utils.uint256ToBytes(cm.sourceChain),
            Utils.uint256ToBytes(cm.targetChain),
            Utils.addressToBytes(cm.targetUser),
            Utils.addressToBytes(cm.payload.targetApp),
            cm.payload.targetFunc,
            cm.payload.targetData
        );
    }

    function hashCM(CrossMessage memory cm) public pure returns (bytes32 x) {
        x = keccak256(cmToBytes(cm));
    }

    function getStorageLocation(uint256 key)
        public
        pure
        returns(bytes32)
    {
        return keccak256(abi.encode(key, 0));
    }

    // storage location of cross-chain message which is on the relay chain
    function getStorageLocationOnRelay(uint256 key)
        public
        pure
        returns(bytes32)
    {
        // storage location for cmHashesOnRelay
        return keccak256(abi.encode(key, 2));
    }

    // for BCR on the relay chain
    function getStorageLocationOfBCROnSource(uint256 key)
    public
        pure
        returns(bytes32)
    {
        // for roots
        // the key is the height of BCR
        return keccak256(abi.encode(key, 1));
    }

    function getStorageLocationOfBCROnRelay(uint256 chain_id, uint256 height)
    public
        pure
        returns(bytes32)
    {
        // for rootsOnRelay
        // the key is the chain_id, height of BCR
        return keccak256(abi.encode(height, keccak256(abi.encode(chain_id, 3))));
    }

    // =========================================== Block-level Cross-chain Root =========================================== 
    uint256 number;
    bytes32 myhash;
    mapping(uint256 => mapping(uint256 => uint256)) hashNum;
    mapping(uint256 => mapping(uint8 => mapping(uint256 => bytes32))) trees;
    mapping(uint256 => uint32) xmcnts;
    mapping(uint256 => uint8) treeFlags;

    function build(uint256 idx, bytes memory data) public {
        bytes32 tempnode = keccak256(data);
        xmcnts[idx] += 1;

        uint32 index = xmcnts[idx];
        // bytes32[] memory nextpaths = new bytes32[](index);
        uint32 point_nextpaths = 0;
        uint8 flag = 2;
        uint8 treeflag = treeFlags[idx];
        uint32 pathpoint = 0;
        while (index >= 1) {
            if (index == 1) {
                roots[idx] = tempnode;
                trees[idx][treeflag][point_nextpaths++] = tempnode;
                break;
            }
            if (index % 2 == 1) {
                if (flag == 2 || flag == 0) {
                    trees[idx][treeflag][point_nextpaths++] = tempnode;
                }
                tempnode = keccak256(abi.encodePacked(tempnode, tempnode));
                flag = 1;
                index = index / 2 + (index % 2);
            } else {
                bytes32 node = trees[idx][1 - treeflag][pathpoint];
                pathpoint += 1;
                if (flag == 1) {
                    trees[idx][treeflag][point_nextpaths++] = node;
                } else if (flag == 2) {
                    flag = 0;
                }
                tempnode = keccak256(abi.encodePacked(node, tempnode));
                index = index / 2 + (index % 2);
            }
        }
        treeFlags[idx] = 1 - treeflag;
        hashNum[idx][xmcnts[idx]] = point_nextpaths;
    }

    function verifyBCR(uint256 index, bytes32 node, bytes32 bcr, bytes32[] memory proof) public view returns(bool) {
        for (uint256 i = 0; i < proof.length; i++){
            bytes32 sible = proof[i];
            if (index % 2 == 1) {
                node = keccak256(abi.encodePacked(sible, node));
            }else{
                node = keccak256(abi.encodePacked(node, sible));
            }
            index /= 2;
        }
        return node == bcr;
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

    // =========================================== Verification =========================================== 

    //functions:deal accept verifyHeader submitHeader decodeProof validateProof 
    mapping(uint256 => mapping(uint256 => StateProofVerifier.BlockHeader)) internal chainToHeaders;

    using RLPReader for RLPReader.RLPItem;
    using RLPReader for bytes;
    constructor () {

    }

    function GetBlockHeader(uint256 chain_id, uint256 _height)
        public
        view
        returns (StateProofVerifier.BlockHeader memory)
    {
        return chainToHeaders[chain_id][_height];
    }

    


    /* @notice submit new blockheader
    *  @author csy
    *  @param payload upperLayer crossChain packet
    *  @return the specific protocol's return data
    */
    function SubmitHeader(uint256 src_chain_id, bytes memory block_data) 
        public 
        returns(bool) 
    {
        StateProofVerifier.BlockHeader memory header;
        RLPReader.RLPItem[] memory headerFields = block_data.toRlpItem().toList();
        header.stateRootHash = bytes32(headerFields[3].toUint());
        header.number = headerFields[8].toUint();
        header.timestamp = headerFields[11].toUint();
        header.hash = keccak256(block_data);
        chainToHeaders[src_chain_id][header.number] = header;
        return true;
    }

    event recordBCR(
        uint256 chain_id,
        uint256 source_height,
        uint256 relay_height,
        bytes32 bcr
    );
    function getBCR(uint256 chain_id, uint256 _height)
        public
        view
        returns (bytes32 bcr)
    {
        return rootsOnRelay[chain_id][_height];
    }
    mapping (bytes32 => uint256) bcrHeightOnRelay;
    function getBCRHeightOnRelay(bytes32 bcr)
        public 
        view
        returns (uint256 height){
            return bcrHeightOnRelay[bcr];
        }
    // used in ToR
    function SubmitHeaderAndBCR(
        uint256 src_chain_id, 
        bytes memory block_data,
        bytes32 bcr, 
        bytes32 position, 
        address sourceAddress, 
        bytes memory accountProof,
        bytes memory storageProof
    ) 
        public 
        returns(bool) 
    {
        StateProofVerifier.BlockHeader memory header;
        RLPReader.RLPItem[] memory headerFields = block_data.toRlpItem().toList();
        header.stateRootHash = bytes32(headerFields[3].toUint());
        header.number = headerFields[8].toUint();
        header.timestamp = headerFields[11].toUint();
        header.hash = keccak256(block_data);
        chainToHeaders[src_chain_id][header.number] = header;
        // verify bcr
        if (bcr != 0x00000000000000000000000000000000){
            verify(position, sourceAddress, abi.encode(bcr), header.stateRootHash, accountProof, storageProof);
            rootsOnRelay[src_chain_id][header.number] = bcr;
            bcrHeightOnRelay[bcr] = block.number;
            emit recordBCR(src_chain_id, header.number, block.number, bcr);
        }
        return true;
    }

    function verify(bytes32 position, address addr, bytes memory data, bytes32 root, bytes memory accountRlpProof,bytes memory storageRlpProof) 
        public pure 
        returns (bool, string memory, uint256)
    {
        RLPReader.RLPItem[] memory accountProof = accountRlpProof.toRlpItem().toList()[0].toList();
        RLPReader.RLPItem[] memory storageProof = storageRlpProof.toRlpItem().toList()[0].toList();
        StateProofVerifier.Account memory extractAccount = StateProofVerifier.extractAccountFromProof(
            keccak256(abi.encodePacked(addr)),
            root,
            accountProof
        );
        // return (true, "");
        if(extractAccount.exists == false) {
            return (false, "extractAccount not exist", 0);
        }
        StateProofVerifier.SlotValue memory slotValue = StateProofVerifier.extractSlotValueFromProof(
            // keccak256(abi.encodePacked(keccak256(abi.encodePacked(kpos, slotNumber)))),
            keccak256(abi.encodePacked(position)),
            // position,
            extractAccount.storageRoot,
            storageProof
        );
        if(slotValue.exists == false) {
            return (false, "slot value not exist", 0);
        }
        if(keccak256(data) != keccak256(abi.encode(slotValue.value))) {
            return (false, "data != value", slotValue.value);
        }
        return (true, "", 0);
    }


    function getStateRoot(uint256 chain_id, uint256 height) 
        internal
        view
        returns (bytes32)
    {
        return chainToHeaders[chain_id][height].stateRootHash;
    }

}