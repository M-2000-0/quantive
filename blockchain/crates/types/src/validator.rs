use serde::{Deserialize, Serialize};

use crate::crypto::*;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Validator {
    pub address: Address,
    pub public_key: PublicKey,
    pub self_stake: Amount,
    pub delegated_stake: Amount,
    pub commission_rate: u16,
    pub endpoint: String,
    pub node_id: String,
    pub is_active: bool,
    pub jail_until: Option<Slot>,
    pub total_stake: Amount,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatorSet {
    pub epoch: Epoch,
    pub validators: Vec<Validator>,
    pub total_stake: Amount,
    pub quorum_size: usize,
    pub max_validators: usize,
}

impl ValidatorSet {
    pub fn new(epoch: Epoch, mut validators: Vec<Validator>, max: usize) -> Self {
        validators.sort_by(|a, b| b.total_stake.cmp(&a.total_stake));
        validators.truncate(max);
        let total_stake = validators.iter().map(|v| v.total_stake).sum();
        let quorum = (validators.len() * 2 / 3) + 1;
        Self { epoch, validators, total_stake, quorum_size: quorum, max_validators: max }
    }

    pub fn contains(&self, address: &Address) -> bool {
        self.validators.iter().any(|v| v.address == *address)
    }

    pub fn proposer_for_slot(&self, slot: Slot) -> Option<&Validator> {
        if self.validators.is_empty() { return None; }
        let idx = slot as usize % self.validators.len();
        Some(&self.validators[idx])
    }

    pub fn len(&self) -> usize { self.validators.len() }
    pub fn is_empty(&self) -> bool { self.validators.is_empty() }
}
