use serde::{Deserialize, Serialize};
use crate::crypto::*;
use crate::crypto::Hash;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountState {
    pub nonce: Nonce,
    pub balance: Amount,
    pub storage_root: Hash,
    pub code_hash: Hash,
    pub last_interaction: Slot,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ChainState {
    pub current_height: u64,
    pub current_slot: Slot,
    pub current_epoch: Epoch,
    pub active_validators: Vec<Address>,
    pub total_supply: Amount,
    pub circulating_supply: Amount,
    pub base_fee: Amount,
    pub next_validator_set_hash: Hash,
}
