use std::sync::Arc;

use tracing::info;

use omnichain_types::*;

use crate::ChainStorage;

/// State snapshot for fast sync and archival.
///
/// Produces periodic snapshots of the full state trie for
/// new nodes to bootstrap without replaying from genesis.
pub struct StateSnapshot {
    pub height: u64,
    pub state_root: Hash,
    pub total_accounts: u64,
    pub total_storage_slots: u64,
    pub data: Vec<u8>,
}

impl StateSnapshot {
    /// Create a snapshot from the current chain state.
    pub fn take(storage: &Arc<ChainStorage>, height: u64) -> Result<Self, Error> {
        let state_root = storage.get_state_root()?
            .ok_or_else(|| Error::Storage("No state root found".into()))?;

        info!("Taking state snapshot at height {}", height);

        // In production: serialize all state trie nodes
        let data = bincode::serialize(&state_root)
            .map_err(|e| Error::Storage(e.to_string()))?;

        Ok(Self {
            height,
            state_root,
            total_accounts: 0,
            total_storage_slots: 0,
            data,
        })
    }

    /// Apply a snapshot to restore state.
    pub fn apply(&self, storage: &Arc<ChainStorage>) -> Result<(), Error> {
        info!("Applying state snapshot at height {}", self.height);
        storage.store_state_root(&self.state_root)?;
        // In production: deserialize and insert all trie nodes
        Ok(())
    }
}
