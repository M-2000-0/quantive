use std::collections::HashMap;
use std::sync::Arc;

use parking_lot::RwLock;

use omnichain_types::*;

mod evm;

pub use evm::*;

/// Parallel execution engine for Omnichain.
pub struct ExecutionEngine {
    state: Arc<RwLock<ExecutionState>>,
    evm: EVMExecutor,
    shard_count: usize,
}

#[derive(Debug, Default)]
pub struct ExecutionState {
    pub accounts: HashMap<Address, AccountState>,
    pub storage: HashMap<(Address, Hash), Hash>,
    pub receipts: Vec<TransactionReceipt>,
    pub block_hashes: HashMap<u64, Hash>,
    pub base_fee: Amount,
}

#[derive(Debug)]
pub struct ExecutionResult {
    pub state_root: Hash,
    pub receipts_root: Hash,
    pub gas_used: GasUnits,
    pub receipts: Vec<TransactionReceipt>,
    pub crosschain_messages: Vec<CrossChainMessage>,
    pub logs: Vec<Log>,
}

impl ExecutionEngine {
    pub fn new(shard_count: usize, chain_id: ChainId) -> Self {
        Self {
            state: Arc::new(RwLock::new(ExecutionState::default())),
            evm: EVMExecutor::new(chain_id),
            shard_count,
        }
    }

    /// Execute a block's transactions in parallel shards.
    pub fn execute_block(&self, block: &Block) -> Result<ExecutionResult, Error> {
        let txs = &block.body.transactions;
        if txs.is_empty() {
            let state_root = self.compute_state_root();
            let receipts_root = self.compute_receipts_root(&[]);
            return Ok(ExecutionResult {
                state_root,
                receipts_root,
                gas_used: 0,
                receipts: vec![],
                crosschain_messages: vec![],
                logs: vec![],
            });
        }
        let shard_size = (txs.len() + self.shard_count - 1) / self.shard_count;
        let chain_id = self.evm.chain_id;

        let mut results = Vec::new();
        for chunk in txs.chunks(shard_size) {
            let txs_to_run: Vec<Transaction> = chunk.to_vec();
            let state = self.state.clone();
            let evm = EVMExecutor::new(chain_id);

            let handle = std::thread::spawn(move || {
                let mut receipts = Vec::new();
                let msgs = Vec::new();
                let mut total_gas = 0u64;
                for tx in &txs_to_run {
                    match &tx.tx_type {
                        TransactionType::NativeTransfer => {
                            let mut s = state.write();
                            let acc = s.accounts.entry(tx.sender).or_insert(AccountState {
                                nonce: 0, balance: 0, storage_root: [0u8; 32],
                                code_hash: [0u8; 32], last_interaction: 0,
                            });
                            acc.nonce += 1;
                            total_gas += 21000;
                        }
                        TransactionType::EVMCall { to, data, value } => {
                            let result = evm.execute_call(tx, &state, to, data, *value);
                            if let Ok(r) = result {
                                total_gas += r.gas_used;
                                receipts.push(r);
                            }
                        }
                        TransactionType::ContractDeploy { code, value } => {
                            let result = evm.execute_deploy(tx, &state, code, *value);
                            if let Ok(r) = result {
                                total_gas += r.gas_used;
                                receipts.push(r);
                            }
                        }
                        TransactionType::CrossChainMessage { .. } => {
                            total_gas += 50000;
                        }
                        _ => {
                            total_gas += 21000;
                        }
                    }
                }
                (receipts, msgs, total_gas)
            });

            results.push(handle);
        }

        let mut all_receipts = Vec::new();
        let mut all_msgs = Vec::new();
        let mut total_gas = 0u64;

        for handle in results {
            let (rec, msgs, gas) = handle.join().map_err(|e| {
                Error::Execution(format!("Thread join failed: {:?}", e))
            })?;
            all_receipts.extend(rec);
            all_msgs.extend(msgs);
            total_gas += gas;
        }

        let state_root = self.compute_state_root();
        let receipts_root = self.compute_receipts_root(&all_receipts);

        Ok(ExecutionResult {
            state_root,
            receipts_root,
            gas_used: total_gas,
            receipts: all_receipts,
            crosschain_messages: all_msgs,
            logs: Vec::new(),
        })
    }

    fn compute_state_root(&self) -> Hash {
        let state = self.state.read();
        let mut hasher = sha3::Sha3_256::new();
        for (addr, acct) in state.accounts.iter() {
            hasher.update(addr);
            hasher.update(&acct.balance.to_le_bytes());
            hasher.update(&acct.nonce.to_le_bytes());
        }
        use sha3::Digest;
        hasher.finalize().into()
    }

    fn compute_receipts_root(&self, receipts: &[TransactionReceipt]) -> Hash {
        let mut hasher = sha3::Sha3_256::new();
        for r in receipts {
            hasher.update(&r.tx_hash);
            hasher.update(&[r.status as u8]);
        }
        use sha3::Digest;
        hasher.finalize().into()
    }

    pub fn state(&self) -> Arc<RwLock<ExecutionState>> {
        self.state.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_transfer(sender: Address, nonce: Nonce) -> Transaction {
        Transaction {
            tx_type: TransactionType::NativeTransfer,
            nonce, sender, gas_limit: 21000,
            max_fee_per_gas: 1_000_000_000, max_priority_fee: 0,
            chain_id: 1, signature: vec![], hash: [0u8; 32],
        }
    }

    #[test]
    fn test_execute_block_empty() {
        let engine = ExecutionEngine::new(4, 1);
        let block = Block {
            header: BlockHeader {
                version: 1, height: 1, slot: 1, epoch: 0,
                parent_hash: [0u8; 32], state_root: [0u8; 32],
                transactions_root: [0u8; 32], receipts_root: [0u8; 32],
                crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
                proposer: [0u8; 20], timestamp: 100, gas_used: 0, gas_limit: 30_000_000,
                extras: vec![], block_type: BlockType::Normal,
            },
            body: BlockBody { transactions: vec![], crosschain_messages: vec![] },
            signature: vec![],
        };
        let result = engine.execute_block(&block).unwrap();
        assert_eq!(result.gas_used, 0);
        assert!(result.receipts.is_empty());
    }

    #[test]
    fn test_execute_transfer_updates_nonce() {
        let engine = ExecutionEngine::new(4, 1);
        let sender = [1u8; 20];
        let tx = make_transfer(sender, 0);
        let block = Block {
            header: BlockHeader {
                version: 1, height: 1, slot: 1, epoch: 0,
                parent_hash: [0u8; 32], state_root: [0u8; 32],
                transactions_root: [0u8; 32], receipts_root: [0u8; 32],
                crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
                proposer: [0u8; 20], timestamp: 100, gas_used: 0, gas_limit: 30_000_000,
                extras: vec![], block_type: BlockType::Normal,
            },
            body: BlockBody { transactions: vec![tx], crosschain_messages: vec![] },
            signature: vec![],
        };
        engine.execute_block(&block).unwrap();
        let state = engine.state();
        let s = state.read();
        let acc = s.accounts.get(&sender).unwrap();
        assert_eq!(acc.nonce, 1);
    }

    #[test]
    fn test_execute_deploy_creates_contract() {
        let engine = ExecutionEngine::new(4, 1);
        let sender = [1u8; 20];
        // Pre-fund the sender
        engine.state().write().accounts.insert(sender, AccountState {
            nonce: 0, balance: 10_000_000, storage_root: [0u8; 32],
            code_hash: [0u8; 32], last_interaction: 0,
        });
        let tx = Transaction {
            tx_type: TransactionType::ContractDeploy { code: vec![0x60, 0x00], value: 0 },
            nonce: 0, sender, gas_limit: 100_000,
            max_fee_per_gas: 1_000_000_000, max_priority_fee: 0,
            chain_id: 1, signature: vec![], hash: [0u8; 32],
        };
        let block = Block {
            header: BlockHeader {
                version: 1, height: 1, slot: 1, epoch: 0,
                parent_hash: [0u8; 32], state_root: [0u8; 32],
                transactions_root: [0u8; 32], receipts_root: [0u8; 32],
                crosschain_messages_root: [0u8; 32], validator_set_hash: [0u8; 32],
                proposer: [0u8; 20], timestamp: 100, gas_used: 0, gas_limit: 30_000_000,
                extras: vec![], block_type: BlockType::Normal,
            },
            body: BlockBody { transactions: vec![tx], crosschain_messages: vec![] },
            signature: vec![],
        };
        let result = engine.execute_block(&block).unwrap();
        assert_eq!(result.receipts.len(), 1);
        assert!(result.receipts[0].contract_address.is_some());
    }
}
