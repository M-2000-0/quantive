use serde::{Deserialize, Serialize};
use sha3::Digest;

use crate::crypto::*;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TransactionType {
    NativeTransfer,
    EVMCall { to: Address, data: Vec<u8>, value: Amount },
    ContractDeploy { code: Vec<u8>, value: Amount },
    CrossChainMessage {
        dest_chain: ChainId,
        dest_contract: Vec<u8>,
        payload: Vec<u8>,
        gas_limit: GasUnits,
    },
    ValidatorStake,
    ValidatorUnstake,
    GovernanceProposal,
    GovernanceVote,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub tx_type: TransactionType,
    pub nonce: Nonce,
    pub sender: Address,
    pub gas_limit: GasUnits,
    pub max_fee_per_gas: Amount,
    pub max_priority_fee: Amount,
    pub chain_id: ChainId,
    pub signature: Vec<u8>,
    pub hash: Hash,
}

impl Transaction {
    pub fn compute_hash(&self) -> Hash {
        let mut hasher = sha3::Sha3_256::new();
        let encoded = bincode::serialize(&self.tx_type).unwrap_or_default();
        hasher.update(&encoded);
        hasher.update(&self.nonce.to_le_bytes());
        hasher.update(&self.sender);
        hasher.update(&self.gas_limit.to_le_bytes());
        hasher.update(&self.chain_id.to_le_bytes());
        hasher.finalize().into()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionReceipt {
    pub tx_hash: Hash,
    pub block_height: u64,
    pub status: bool,
    pub gas_used: GasUnits,
    pub cumulative_gas_used: GasUnits,
    pub contract_address: Option<Address>,
    pub logs: Vec<Log>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Log {
    pub address: Address,
    pub topics: Vec<Hash>,
    pub data: Vec<u8>,
}
