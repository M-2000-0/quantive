use serde::{Deserialize, Serialize};
use sha3::Digest;

use crate::crypto::*;
use crate::transaction::Transaction;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum BlockType {
    Genesis,
    Normal,
    CrossChain,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrossChainMessage {
    pub source_chain: ChainId,
    pub dest_chain: ChainId,
    pub sender: Vec<u8>,
    pub recipient: Vec<u8>,
    pub payload: Vec<u8>,
    pub nonce: u64,
    pub block_height: u64,
    pub proof: Vec<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockHeader {
    pub version: u32,
    pub height: u64,
    pub slot: Slot,
    pub epoch: Epoch,
    pub parent_hash: Hash,
    pub state_root: Hash,
    pub transactions_root: Hash,
    pub receipts_root: Hash,
    pub crosschain_messages_root: Hash,
    pub validator_set_hash: Hash,
    pub proposer: Address,
    pub timestamp: TimestampSecs,
    pub gas_used: GasUnits,
    pub gas_limit: GasUnits,
    pub extras: Vec<u8>,
    pub block_type: BlockType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub header: BlockHeader,
    pub body: BlockBody,
    pub signature: Vec<u8>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockBody {
    pub transactions: Vec<Transaction>,
    pub crosschain_messages: Vec<CrossChainMessage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedBlock {
    pub block: Block,
    pub commit_qc: Vec<ValidatorVote>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatorVote {
    pub validator: Address,
    pub signature: Vec<u8>,
    pub round: u64,
    pub vote_type: VoteType,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum VoteType {
    PreVote,
    PreCommit,
    Commit,
}

impl Block {
    pub fn compute_hash(&self) -> Hash {
        let mut hasher = sha3::Sha3_256::new();
        let encoded = bincode::serialize(&self.header).unwrap_or_default();
        hasher.update(&encoded);
        hasher.finalize().into()
    }
}
