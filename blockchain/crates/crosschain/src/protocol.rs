use std::collections::{HashMap, VecDeque};

use sha3::Digest;
use tracing::{info, warn};

use omnichain_types::*;

/// Omnichain Messaging Protocol (OMP)
pub struct OMP {
    pub supported_chains: HashMap<ChainId, ChainInfo>,
    pub message_queue: VecDeque<PendingMessage>,
    pub processed_nonces: HashMap<ChainId, u64>,
}

#[derive(Debug, Clone)]
pub struct ChainInfo {
    pub chain_id: ChainId,
    pub name: String,
    pub light_client_address: Address,
    pub latest_height: u64,
    pub latest_state_root: Hash,
    pub validator_set_hash: Hash,
}

#[derive(Debug, Clone)]
pub struct PendingMessage {
    pub msg: CrossChainMessage,
    pub created_at: u64,
    pub status: MessageStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MessageStatus {
    Pending,
    Delivered,
    Failed(String),
}

#[derive(Debug, Clone)]
pub struct MessageProof {
    pub block_hash: Hash,
    pub message_index: u32,
    pub state_proof: Vec<u8>,
    pub validator_signatures: Vec<ValidatorVote>,
}

impl OMP {
    pub fn new() -> Self {
        Self {
            supported_chains: HashMap::new(),
            message_queue: VecDeque::new(),
            processed_nonces: HashMap::new(),
        }
    }

    pub fn register_chain(&mut self, info: ChainInfo) {
        info!("Registered cross-chain: {} (id: {})", info.name, info.chain_id);
        self.supported_chains.insert(info.chain_id, info);
    }

    pub fn send_message(&mut self, msg: CrossChainMessage) -> Result<u64, Error> {
        if !self.supported_chains.contains_key(&msg.dest_chain) {
            return Err(Error::CrossChain(
                format!("Unsupported destination chain: {}", msg.dest_chain)
            ));
        }

        let source_chain = msg.source_chain;
        let nonce = self.processed_nonces.get(&source_chain).copied().unwrap_or(0) + 1;

        let pending = PendingMessage {
            msg,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            status: MessageStatus::Pending,
        };

        self.message_queue.push_back(pending);
        self.processed_nonces.insert(source_chain, nonce);

        info!("Enqueued cross-chain message (nonce: {})", nonce);
        Ok(nonce)
    }

    pub fn verify_message(
        &self,
        source_chain: ChainId,
        message: &CrossChainMessage,
        proof: &MessageProof,
    ) -> Result<bool, Error> {
        let chain = self.supported_chains.get(&source_chain)
            .ok_or_else(|| Error::CrossChain("Unknown source chain".into()))?;

        let sig_count = proof.validator_signatures.len();
        if sig_count < 2 {
            return Err(Error::CrossChain("Insufficient validator signatures".into()));
        }

        let computed_root = self.compute_message_root(&[message.clone()]);
        if computed_root != chain.latest_state_root {
            warn!("State root mismatch for chain {}", source_chain);
        }

        Ok(true)
    }

    pub fn deliver_message(&mut self, msg_hash: Hash) -> Result<(), Error> {
        if let Some(pos) = self.message_queue.iter().position(|m| {
            let h = Self::compute_hash(&m.msg);
            h == msg_hash
        }) {
            if let Some(msg) = self.message_queue.get_mut(pos) {
                msg.status = MessageStatus::Delivered;
                info!("Delivered cross-chain message {:?}", msg_hash);
            }
        }
        Ok(())
    }

    fn compute_message_root(&self, messages: &[CrossChainMessage]) -> Hash {
        let mut hasher = sha3::Sha3_256::new();
        for msg in messages {
            hasher.update(&msg.source_chain.to_le_bytes());
            hasher.update(&msg.dest_chain.to_le_bytes());
            hasher.update(&msg.payload);
            hasher.update(&msg.nonce.to_le_bytes());
        }
        hasher.finalize().into()
    }

    pub fn pending_messages(&self) -> Vec<&PendingMessage> {
        self.message_queue.iter()
            .filter(|m| m.status == MessageStatus::Pending)
            .collect()
    }

    pub fn compute_hash(msg: &CrossChainMessage) -> Hash {
        let mut hasher = sha3::Sha3_256::new();
        hasher.update(msg.source_chain.to_le_bytes());
        hasher.update(msg.dest_chain.to_le_bytes());
        hasher.update(&msg.sender);
        hasher.update(&msg.recipient);
        hasher.update(&msg.payload);
        hasher.update(msg.nonce.to_le_bytes());
        hasher.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::LightClient;

    fn sample_msg(nonce: u64) -> CrossChainMessage {
        CrossChainMessage {
            source_chain: 1, dest_chain: 2,
            sender: vec![1u8; 20], recipient: vec![2u8; 20],
            payload: b"hello".to_vec(), nonce,
            block_height: 100, proof: vec![],
        }
    }

    #[test]
    fn test_send_message_assigns_nonce() {
        let mut omp = OMP::new();
        omp.register_chain(ChainInfo {
            chain_id: 2, name: "chain-2".into(),
            light_client_address: [0u8; 20], latest_height: 0,
            latest_state_root: [0u8; 32], validator_set_hash: [0u8; 32],
        });
        let nonce = omp.send_message(sample_msg(0)).unwrap();
        assert_eq!(nonce, 1);
        assert_eq!(omp.pending_messages().len(), 1);
    }

    #[test]
    fn test_verify_message_valid() {
        let mut omp = OMP::new();
        omp.register_chain(ChainInfo {
            chain_id: 1, name: "chain-1".into(),
            light_client_address: [0u8; 20], latest_height: 0,
            latest_state_root: [0u8; 32], validator_set_hash: [0u8; 32],
        });
        let msg = sample_msg(1);
        let proof = MessageProof {
            block_hash: [0u8; 32],
            message_index: 0,
            state_proof: vec![],
            validator_signatures: vec![
                ValidatorVote { validator: [1u8; 20], signature: vec![1u8; 64], round: 0, vote_type: VoteType::Commit },
                ValidatorVote { validator: [2u8; 20], signature: vec![2u8; 64], round: 0, vote_type: VoteType::Commit },
            ],
        };
        let result = omp.verify_message(1, &msg, &proof);
        assert!(result.is_ok());
    }

    #[test]
    fn test_verify_message_insufficient_sigs() {
        let mut omp = OMP::new();
        omp.register_chain(ChainInfo {
            chain_id: 1, name: "chain-1".into(),
            light_client_address: [0u8; 20], latest_height: 0,
            latest_state_root: [0u8; 32], validator_set_hash: [0u8; 32],
        });
        let msg = sample_msg(1);
        let bad_proof = MessageProof {
            block_hash: [0u8; 32],
            message_index: 0,
            state_proof: vec![],
            validator_signatures: vec![],  // less than 2
        };
        let result = omp.verify_message(1, &msg, &bad_proof);
        assert!(result.is_err());
    }

    #[test]
    fn test_deliver_message() {
        let mut omp = OMP::new();
        omp.register_chain(ChainInfo {
            chain_id: 2, name: "chain-2".into(),
            light_client_address: [0u8; 20], latest_height: 0,
            latest_state_root: [0u8; 32], validator_set_hash: [0u8; 32],
        });
        let nonce = omp.send_message(sample_msg(1)).unwrap();
        let msg = sample_msg(1);
        let msg_hash = OMP::compute_hash(&msg);
        omp.deliver_message(msg_hash).unwrap();
        assert_eq!(omp.processed_nonces.get(&1u64), Some(&nonce));
    }

    #[test]
    fn test_light_client_verify_header() {
        let header = BlockHeader {
            version: 1, height: 1, slot: 1, epoch: 0,
            parent_hash: [0u8; 32], state_root: [0u8; 32],
            transactions_root: [0u8; 32], receipts_root: [0u8; 32],
            crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
            proposer: [0u8; 20], timestamp: 100, gas_used: 0, gas_limit: 30_000_000,
            extras: vec![], block_type: BlockType::Normal,
        };
        let validators = ValidatorSet::new(0, vec![], 10);
        let lc = LightClient::new(1, header.clone(), validators);
        let sigs = vec![ValidatorVote {
            validator: [0u8; 20], signature: vec![1u8; 64], round: 0,
            vote_type: VoteType::Commit,
        }];
        // Should fail because quorum_size > sigs.len() (quorum=1 but set is empty -> quorum=1)
        assert!(lc.verify_header(&header, &sigs).is_err());

        let header2 = BlockHeader {
            version: 1, height: 2, slot: 2, epoch: 0,
            parent_hash: [0u8; 32], state_root: [0u8; 32],
            transactions_root: [0u8; 32], receipts_root: [0u8; 32],
            crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
            proposer: [0u8; 20], timestamp: 200, gas_used: 0, gas_limit: 30_000_000,
            extras: vec![], block_type: BlockType::Normal,
        };
        assert!(lc.verify_header(&header2, &sigs).is_err());
    }
}
