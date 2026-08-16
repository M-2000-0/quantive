use omnichain_types::*;

use crate::protocol::{MessageProof, OMP};

/// Relayer service that forwards cross-chain messages between chains.
///
/// Relayers are incentivized via fees from the OMP protocol.
/// Any node can run a relayer; relayers are selected round-robin per epoch.
pub struct Relayer {
    pub chain_id: ChainId,
    pub private_key: Vec<u8>,
    pub connected_relayers: Vec<RelayerPeer>,
}

#[derive(Debug, Clone)]
pub struct RelayerPeer {
    pub chain_id: ChainId,
    pub endpoint: String,
    pub public_key: Vec<u8>,
}

impl Relayer {
    pub fn new(chain_id: ChainId, private_key: Vec<u8>) -> Self {
        Self {
            chain_id,
            private_key,
            connected_relayers: Vec::new(),
        }
    }

    /// Submit a proof for a cross-chain message to the destination chain.
    pub fn submit_message_proof(
        &self,
        message: &CrossChainMessage,
        _proof: MessageProof,
        _dest_endpoint: &str,
    ) -> Result<(), Error> {
        tracing::info!(
            "Relaying message {} → chain {} (nonce: {})",
            hex::encode(&message.sender[..4.min(message.sender.len())]),
            message.dest_chain,
            message.nonce,
        );
        // In production: submit proof via JSON-RPC to destination node
        Ok(())
    }

    /// Collect pending messages from the OMP queue and batch them.
    pub fn collect_pending(&self, omp: &OMP) -> Vec<CrossChainMessage> {
        omp.pending_messages()
            .iter()
            .map(|p| p.msg.clone())
            .collect()
    }

    /// Register with a remote relayer network.
    pub fn connect(&mut self, peer: RelayerPeer) {
        tracing::info!("Connected to relayer on chain {} at {}", peer.chain_id, peer.endpoint);
        self.connected_relayers.push(peer);
    }
}
