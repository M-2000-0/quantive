pub mod block;
pub mod transaction;
pub mod validator;
pub mod state;
pub mod crypto;
pub mod error;

pub use block::*;
pub use transaction::*;
pub use validator::*;
pub use state::*;
pub use crypto::*;
pub use error::*;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_hash() {
        let block = Block {
            header: BlockHeader {
                version: 1, height: 0, slot: 0, epoch: 0,
                parent_hash: [0u8; 32], state_root: [0u8; 32],
                transactions_root: [0u8; 32], receipts_root: [0u8; 32],
                crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
                proposer: [0u8; 20], timestamp: 0, gas_used: 0, gas_limit: 30_000_000,
                extras: vec![], block_type: BlockType::Genesis,
            },
            body: BlockBody { transactions: vec![], crosschain_messages: vec![] },
            signature: vec![],
        };
        let hash = block.compute_hash();
        assert_eq!(hash.len(), 32);
        assert_ne!(hash, [0u8; 32]);
    }

    #[test]
    fn test_transaction_hash() {
        let tx = Transaction {
            tx_type: TransactionType::NativeTransfer,
            nonce: 0, sender: [1u8; 20], gas_limit: 21000,
            max_fee_per_gas: 1_000_000_000, max_priority_fee: 0,
            chain_id: 1, signature: vec![], hash: [0u8; 32],
        };
        let hash = tx.compute_hash();
        assert_eq!(hash.len(), 32);
        assert_ne!(hash, [0u8; 32]);
    }

    #[test]
    fn test_validator_set_quorum() {
        let mut validators = vec![];
        for i in 0..10 {
            validators.push(Validator {
                address: [i as u8; 20], public_key: [i as u8; 32],
                self_stake: 1000, delegated_stake: 0, commission_rate: 10,
                endpoint: String::new(), node_id: String::new(),
                is_active: true, jail_until: None, total_stake: 1000,
            });
        }
        let set = ValidatorSet::new(1, validators, 10);
        assert_eq!(set.quorum_size, 7);
        assert_eq!(set.len(), 10);
    }

    #[test]
    fn test_validator_set_contains() {
        let addr = [42u8; 20];
        let v = Validator {
            address: addr, public_key: [0u8; 32], self_stake: 1000,
            delegated_stake: 0, commission_rate: 10, endpoint: String::new(),
            node_id: String::new(), is_active: true, jail_until: None, total_stake: 1000,
        };
        let set = ValidatorSet::new(0, vec![v], 10);
        assert!(set.contains(&addr));
        assert!(!set.contains(&[99u8; 20]));
    }

    #[test]
    fn test_validator_set_sorts_by_stake() {
        let validators = vec![
            Validator {
                address: [1u8; 20], public_key: [0u8; 32], self_stake: 500,
                delegated_stake: 0, commission_rate: 10, endpoint: String::new(),
                node_id: String::new(), is_active: true, jail_until: None, total_stake: 500,
            },
            Validator {
                address: [2u8; 20], public_key: [0u8; 32], self_stake: 1500,
                delegated_stake: 0, commission_rate: 10, endpoint: String::new(),
                node_id: String::new(), is_active: true, jail_until: None, total_stake: 1500,
            },
        ];
        let set = ValidatorSet::new(0, validators, 10);
        assert_eq!(set.validators[0].total_stake, 1500);
        assert_eq!(set.validators[1].total_stake, 500);
    }
}
