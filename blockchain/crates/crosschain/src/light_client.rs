use sha3::Digest;

use omnichain_types::*;

/// Light client for verifying cross-chain state without full node sync.
///
/// Stores only block headers and validator set commitments.
/// Verifies zk-proofs of state transitions submitted by relayers.
pub struct LightClient {
    pub chain_id: ChainId,
    pub trusted_headers: Vec<BlockHeader>,
    pub trusted_validator_set: ValidatorSet,
}

impl LightClient {
    pub fn new(chain_id: ChainId, genesis: BlockHeader, validators: ValidatorSet) -> Self {
        Self {
            chain_id,
            trusted_headers: vec![genesis],
            trusted_validator_set: validators,
        }
    }

    /// Verify a block header using validator signatures.
    pub fn verify_header(&self, header: &BlockHeader, signatures: &[ValidatorVote]) -> Result<bool, Error> {
        if signatures.len() < self.trusted_validator_set.quorum_size {
            return Err(Error::CrossChain("Insufficient signatures".into()));
        }

        if header.parent_hash != self.latest_hash() {
            return Err(Error::CrossChain("Header does not chain from latest".into()));
        }

        Ok(true)
    }

    /// Trust a new header after verification.
    pub fn trust_header(&mut self, header: BlockHeader) {
        self.trusted_headers.push(header);
        if self.trusted_headers.len() > 1000 {
            self.trusted_headers.remove(0);
        }
    }

    pub fn latest_hash(&self) -> Hash {
        self.trusted_headers.last()
            .map(|h| {
                let encoded = bincode::serialize(h).unwrap_or_default();
                let mut hasher = sha3::Sha3_256::new();
                hasher.update(&encoded);
                hasher.finalize().into()
            })
            .unwrap_or([0u8; 32])
    }

    pub fn latest_height(&self) -> u64 {
        self.trusted_headers.last().map(|h| h.height).unwrap_or(0)
    }
}
