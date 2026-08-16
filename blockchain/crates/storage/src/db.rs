use std::path::Path;
use std::sync::Arc;

use sled::Db;
use tracing::info;

use omnichain_types::*;

/// Persistent key-value storage using Sled (embedded database).
///
/// Column families (trees):
/// - `blocks`: height → Block
/// - `block_hash`: block_hash → height
/// - `txs`: tx_hash → Transaction
/// - `state`: account trie nodes
/// - `code`: code_hash → bytecode
/// - `headers`: height → BlockHeader
/// - `validators`: epoch → ValidatorSet
/// - `receipts`: tx_hash → TransactionReceipt
/// - `crosschain`: cross-chain message store
/// - `metadata`: chain metadata
pub struct ChainStorage {
    pub db: Arc<Db>,
}

impl ChainStorage {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, Error> {
        let db = sled::open(&path)
            .map_err(|e| Error::Storage(format!("Failed to open sled db: {}", e)))?;

        // Ensure column families exist
        for tree in &["blocks", "block_hash", "txs", "state", "code",
                       "headers", "validators", "receipts", "crosschain", "metadata"]
        {
            let _ = db.open_tree(tree)
                .map_err(|e| Error::Storage(format!("Failed to open tree '{}': {}", tree, e)))?;
        }

        info!("Storage opened at: {}", path.as_ref().display());
        Ok(Self { db: Arc::new(db) })
    }

    // --- Blocks ---

    pub fn store_block(&self, block: &Block) -> Result<(), Error> {
        let bytes = bincode::serialize(block)
            .map_err(|e| Error::Storage(format!("Serialize block: {}", e)))?;
        let key = bincode::serialize(&block.header.height)
            .map_err(|e| Error::Storage(format!("Serialize height: {}", e)))?;
        self.db
            .open_tree("blocks")
            .map_err(|e| Error::Storage(e.to_string()))?
            .insert(key, bytes)
            .map_err(|e| Error::Storage(e.to_string()))?;
        Ok(())
    }

    pub fn get_block(&self, height: u64) -> Result<Option<Block>, Error> {
        let key = bincode::serialize(&height)
            .map_err(|e| Error::Storage(format!("Serialize height: {}", e)))?;
        let tree = self.db.open_tree("blocks")
            .map_err(|e| Error::Storage(e.to_string()))?;
        match tree.get(key).map_err(|e| Error::Storage(e.to_string()))? {
            Some(bytes) => {
                let block = bincode::deserialize(&bytes)
                    .map_err(|e| Error::Storage(format!("Deserialize block: {}", e)))?;
                Ok(Some(block))
            }
            None => Ok(None),
        }
    }

    pub fn latest_block(&self) -> Result<Option<Block>, Error> {
        let tree = self.db.open_tree("blocks")
            .map_err(|e| Error::Storage(e.to_string()))?;
        if let Some((_, value)) = tree.last()
            .map_err(|e| Error::Storage(e.to_string()))?
        {
            let block = bincode::deserialize(&value)
                .map_err(|e| Error::Storage(format!("Deserialize block: {}", e)))?;
            Ok(Some(block))
        } else {
            Ok(None)
        }
    }

    // --- Transactions ---

    pub fn store_transaction(&self, tx: &Transaction) -> Result<(), Error> {
        let bytes = bincode::serialize(tx)
            .map_err(|e| Error::Storage(format!("Serialize tx: {}", e)))?;
        self.db
            .open_tree("txs")
            .map_err(|e| Error::Storage(e.to_string()))?
            .insert(tx.hash, bytes)
            .map_err(|e| Error::Storage(e.to_string()))?;
        Ok(())
    }

    pub fn get_transaction(&self, hash: &Hash) -> Result<Option<Transaction>, Error> {
        let tree = self.db.open_tree("txs")
            .map_err(|e| Error::Storage(e.to_string()))?;
        match tree.get(hash).map_err(|e| Error::Storage(e.to_string()))? {
            Some(bytes) => {
                let tx = bincode::deserialize(&bytes)
                    .map_err(|e| Error::Storage(format!("Deserialize tx: {}", e)))?;
                Ok(Some(tx))
            }
            None => Ok(None),
        }
    }

    // --- State ---

    pub fn store_state_root(&self, root: &Hash) -> Result<(), Error> {
        self.db
            .open_tree("metadata")
            .map_err(|e| Error::Storage(e.to_string()))?
            .insert(b"state_root", root)
            .map_err(|e| Error::Storage(e.to_string()))?;
        Ok(())
    }

    pub fn get_state_root(&self) -> Result<Option<Hash>, Error> {
        let tree = self.db.open_tree("metadata")
            .map_err(|e| Error::Storage(e.to_string()))?;
        match tree.get(b"state_root").map_err(|e| Error::Storage(e.to_string()))? {
            Some(bytes) => {
                let mut root = [0u8; 32];
                root.copy_from_slice(&bytes);
                Ok(Some(root))
            }
            None => Ok(None),
        }
    }

    // --- Validators ---

    pub fn store_validators(&self, epoch: u64, set: &ValidatorSet) -> Result<(), Error> {
        let key = bincode::serialize(&epoch)
            .map_err(|e| Error::Storage(format!("Serialize epoch: {}", e)))?;
        let bytes = bincode::serialize(set)
            .map_err(|e| Error::Storage(format!("Serialize validator set: {}", e)))?;
        self.db
            .open_tree("validators")
            .map_err(|e| Error::Storage(e.to_string()))?
            .insert(key, bytes)
            .map_err(|e| Error::Storage(e.to_string()))?;
        Ok(())
    }

    pub fn get_validators(&self, epoch: u64) -> Result<Option<ValidatorSet>, Error> {
        let key = bincode::serialize(&epoch)
            .map_err(|e| Error::Storage(format!("Serialize epoch: {}", e)))?;
        let tree = self.db.open_tree("validators")
            .map_err(|e| Error::Storage(e.to_string()))?;
        match tree.get(key).map_err(|e| Error::Storage(e.to_string()))? {
            Some(bytes) => {
                let set = bincode::deserialize(&bytes)
                    .map_err(|e| Error::Storage(format!("Deserialize validators: {}", e)))?;
                Ok(Some(set))
            }
            None => Ok(None),
        }
    }
}

impl Drop for ChainStorage {
    fn drop(&mut self) {
        let _ = self.db.flush();
    }
}
