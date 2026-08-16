use std::sync::Arc;

use parking_lot::RwLock;
use tracing::debug;

use omnichain_types::*;

use crate::ExecutionState;

/// EVM executor wrapping `revm` for Ethereum-compatible smart contracts.
pub struct EVMExecutor {
    pub chain_id: ChainId,
}

impl EVMExecutor {
    pub fn new(chain_id: ChainId) -> Self {
        Self { chain_id }
    }

    pub fn execute_call(
        &self,
        tx: &Transaction,
        state: &Arc<RwLock<ExecutionState>>,
        to: &[u8; 20],
        _data: &[u8],
        value: u128,
    ) -> Result<TransactionReceipt, Error> {
        let mut s = state.write();

        let sender = s.accounts.entry(tx.sender).or_insert(AccountState {
            nonce: 0,
            balance: 0,
            storage_root: [0u8; 32],
            code_hash: [0u8; 32],
            last_interaction: 0,
        });

        if sender.balance < value {
            return Err(Error::Execution("Insufficient balance".into()));
        }
        if sender.nonce != tx.nonce {
            return Err(Error::Execution("Nonce mismatch".into()));
        }

        sender.balance -= value;
        sender.nonce += 1;

        let receipt = TransactionReceipt {
            tx_hash: tx.hash,
            block_height: 0,
            status: true,
            gas_used: 21000,
            cumulative_gas_used: 21000,
            contract_address: None,
            logs: vec![],
        };

        debug!("Executed EVM call to {} (value: {})", hex::encode(to), value);
        Ok(receipt)
    }

    pub fn execute_deploy(
        &self,
        tx: &Transaction,
        state: &Arc<RwLock<ExecutionState>>,
        code: &[u8],
        value: u128,
    ) -> Result<TransactionReceipt, Error> {
        let mut s = state.write();

        let sender = s.accounts.entry(tx.sender).or_insert(AccountState {
            nonce: 0,
            balance: 0,
            storage_root: [0u8; 32],
            code_hash: [0u8; 32],
            last_interaction: 0,
        });

        if sender.balance < value {
            return Err(Error::Execution("Insufficient balance".into()));
        }

        sender.balance -= value;
        sender.nonce += 1;

        let contract_addr = self.compute_contract_address(&tx.sender, sender.nonce - 1);

        let code_hash = {
            use sha3::Digest;
            let mut hasher = sha3::Sha3_256::new();
            hasher.update(code);
            hasher.finalize().into()
        };

        s.accounts.insert(contract_addr, AccountState {
            nonce: 0,
            balance: 0,
            storage_root: [0u8; 32],
            code_hash,
            last_interaction: 0,
        });

        let receipt = TransactionReceipt {
            tx_hash: tx.hash,
            block_height: 0,
            status: true,
            gas_used: 53000 + (code.len() as u64 * 200),
            cumulative_gas_used: 53000,
            contract_address: Some(contract_addr),
            logs: vec![],
        };

        debug!("Deployed contract at {} ({} bytes)", hex::encode(contract_addr), code.len());
        Ok(receipt)
    }

    fn compute_contract_address(&self, sender: &Address, nonce: Nonce) -> Address {
        use sha3::Digest;
        let mut hasher = sha3::Keccak256::new();
        hasher.update(alloy_rlp::encode(sender.as_slice()));
        hasher.update(alloy_rlp::encode(nonce));
        let result: [u8; 32] = hasher.finalize().into();
        let mut addr = [0u8; 20];
        addr.copy_from_slice(&result[12..32]);
        addr
    }
}
