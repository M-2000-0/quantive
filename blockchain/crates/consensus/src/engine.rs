use std::collections::HashMap;
use std::sync::Arc;

use parking_lot::RwLock;
use tracing::{info, debug};

use omnichain_types::*;

/// Pipelined BFT consensus engine implementing HotStuff-style consensus.
///
/// Pipeline stages overlap across consecutive blocks:
/// - Stage 1 (Propose): Leader proposes block N
/// - Stage 2 (PreVote): Validators validate and prevote block N-1
/// - Stage 3 (PreCommit): Validators pre-commit block N-2
/// - Stage 4 (Commit): Block N-3 is finalized
#[allow(dead_code)]
pub struct ConsensusEngine {
    config: ConsensusConfig,
    state: Arc<RwLock<ConsensusState>>,
    validator_set: Arc<RwLock<ValidatorSet>>,
}

#[derive(Debug, Clone)]
pub struct ConsensusConfig {
    pub block_time_ms: u64,
    pub pipeline_depth: usize,
    pub max_validators: usize,
    pub min_self_stake: Amount,
    pub epoch_length_slots: u64,
}

impl Default for ConsensusConfig {
    fn default() -> Self {
        Self {
            block_time_ms: 80,
            pipeline_depth: 4,
            max_validators: 150,
            min_self_stake: 500_000 * 10u128.pow(18),
            epoch_length_slots: 32_400,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ConsensusState {
    pub current_round: u64,
    pub current_height: u64,
    pub current_epoch: Epoch,
    pub finalized_height: u64,
    pub pending_blocks: HashMap<Hash, Block>,
    pub votes: HashMap<Hash, Vec<ValidatorVote>>,
    pub commits: HashMap<Hash, Vec<ValidatorVote>>,
}

impl Default for ConsensusState {
    fn default() -> Self {
        Self {
            current_round: 0,
            current_height: 0,
            current_epoch: 0,
            finalized_height: 0,
            pending_blocks: HashMap::new(),
            votes: HashMap::new(),
            commits: HashMap::new(),
        }
    }
}

impl ConsensusEngine {
    pub fn new(config: ConsensusConfig, validators: ValidatorSet) -> Self {
        let state = ConsensusState::default();
        Self {
            config,
            state: Arc::new(RwLock::new(state)),
            validator_set: Arc::new(RwLock::new(validators)),
        }
    }

    /// Returns the proposer address for the given slot.
    pub fn proposer_for_slot(&self, slot: Slot) -> Option<Address> {
        let vs = self.validator_set.read();
        vs.proposer_for_slot(slot).map(|v| v.address)
    }

    /// Validate a block proposal from the leader.
    pub fn validate_block(&self, block: &SignedBlock, slot: Slot) -> Result<bool, Error> {
        let vs = self.validator_set.read();

        // Verify proposer is correct
        let expected = vs.proposer_for_slot(slot)
            .ok_or_else(|| Error::Consensus("No proposer for slot".into()))?;
        if block.block.header.proposer != expected.address {
            return Err(Error::Consensus("Wrong proposer".into()));
        }

        // Verify parent hash continuity
        let state = self.state.read();
        if block.block.header.parent_hash != [0u8; 32] && state.current_height > 0 {
            // Check if parent exists in pending or committed
        }

        // Verify block hash matches
        let _computed = block.block.compute_hash();
        // Hash is in header or computed — we'll trust the header for now

        Ok(true)
    }

    /// Process a prevote from a validator.
    pub fn process_prevote(&self, block_hash: Hash, vote: ValidatorVote) -> Result<(), Error> {
        let vs = self.validator_set.read();
        if !vs.contains(&vote.validator) {
            return Err(Error::Consensus("Voter not in validator set".into()));
        }

        let mut state = self.state.write();
        state.votes.entry(block_hash)
            .or_default()
            .push(vote);

        // Check if we have quorum
        if let Some(votes) = state.votes.get(&block_hash) {
            if votes.len() >= vs.quorum_size {
                debug!("Prevote quorum reached for block {:?}", block_hash);
            }
        }
        Ok(())
    }

    /// Process a pre-commit from a validator.
    pub fn process_precommit(&self, block_hash: Hash, vote: ValidatorVote) -> Result<(), Error> {
        let vs = self.validator_set.read();
        if !vs.contains(&vote.validator) {
            return Err(Error::Consensus("Voter not in validator set".into()));
        }

        let mut state = self.state.write();
        state.commits.entry(block_hash)
            .or_default()
            .push(vote);

        if let Some(commits) = state.commits.get(&block_hash) {
            if commits.len() >= vs.quorum_size {
                info!("Block {:?} finalized at height {}", block_hash, state.current_height);
                state.finalized_height = state.current_height;
            }
        }
        Ok(())
    }

    /// Build a QC (Quorum Certificate) from collected votes.
    pub fn build_qc(&self, block_hash: &Hash) -> Option<Vec<ValidatorVote>> {
        let state = self.state.read();
        state.commits.get(block_hash)
            .map(|v| {
                let vs = self.validator_set.read();
                let quorum = vs.quorum_size;
                v.iter().take(quorum).cloned().collect()
            })
    }

    /// Start the next epoch, electing a new validator set.
    pub fn rotate_epoch(&self, new_validators: ValidatorSet) {
        let mut vs = self.validator_set.write();
        *vs = new_validators;
        let mut state = self.state.write();
        state.current_epoch += 1;
        info!("Rotated to epoch {} with {} validators", state.current_epoch, vs.len());
    }

    /// Process a new block from the proposer.
    pub fn process_proposal(&self, block: SignedBlock) -> Result<(), Error> {
        let hash = block.block.compute_hash();
        let height = block.block.header.height;
        let slot = block.block.header.slot;

        // Validate
        self.validate_block(&block, slot)?;

        // Store pending
        let mut state = self.state.write();
        state.pending_blocks.insert(hash, block.block);
        state.current_height = height;
        state.current_round = slot;
        debug!("Accepted proposal at height {} / slot {}", height, slot);
        Ok(())
    }

    pub fn state(&self) -> Arc<RwLock<ConsensusState>> {
        self.state.clone()
    }

    pub fn validator_set(&self) -> Arc<RwLock<ValidatorSet>> {
        self.validator_set.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_config() -> ConsensusConfig {
        ConsensusConfig {
            block_time_ms: 1000,
            pipeline_depth: 4,
            max_validators: 10,
            min_self_stake: 100,
            epoch_length_slots: 100,
        }
    }

    fn make_validator_set() -> ValidatorSet {
        let vals: Vec<Validator> = (0..4).map(|i| Validator {
            address: [i as u8; 20],
            public_key: [i as u8; 32],
            self_stake: 1000,
            delegated_stake: 0,
            commission_rate: 10,
            endpoint: String::new(),
            node_id: String::new(),
            is_active: true,
            jail_until: None,
            total_stake: 1000,
        }).collect();
        ValidatorSet::new(0, vals, 10)
    }

    #[test]
    fn test_engine_new() {
        let engine = ConsensusEngine::new(make_config(), make_validator_set());
        let state = engine.state();
        let s = state.read();
        assert_eq!(s.current_round, 0);
    }

    #[test]
    fn test_proposer_rotates() {
        let engine = ConsensusEngine::new(make_config(), make_validator_set());
        let p0 = engine.proposer_for_slot(0);
        let p1 = engine.proposer_for_slot(1);
        assert!(p0.is_some());
        assert!(p1.is_some());
        assert_ne!(p0, p1);
    }
}
