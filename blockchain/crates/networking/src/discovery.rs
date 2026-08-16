use std::collections::HashSet;

use libp2p::Multiaddr;
use tracing::info;

use omnichain_types::Error;

/// Bootstrap peers for initial network discovery.
pub const BOOTSTRAP_PEERS: &[&str] = &[
    "/ip4/134.209.0.1/tcp/30333/p2p/12D3KooW...",
    "/ip4/167.71.0.2/tcp/30333/p2p/12D3KooX...",
];

pub struct PeerDiscovery {
    pub bootstraps: Vec<Multiaddr>,
    pub routing_table: HashSet<String>,
}

impl PeerDiscovery {
    pub fn new(bootstraps: Vec<Multiaddr>) -> Self {
        Self {
            bootstraps,
            routing_table: HashSet::new(),
        }
    }

    pub fn with_default_bootstraps() -> Result<Self, Error> {
        let addrs: Vec<Multiaddr> = BOOTSTRAP_PEERS
            .iter()
            .filter_map(|s| s.parse::<Multiaddr>().ok())
            .collect();

        if addrs.is_empty() {
            return Err(Error::Network("No valid bootstrap addresses".into()));
        }

        Ok(Self::new(addrs))
    }

    /// Add a discovered peer to the routing table.
    pub fn add_peer(&mut self, peer_id: String, addr: Multiaddr) {
        self.routing_table.insert(peer_id);
        info!("Discovered peer: {}", addr);
    }

    pub fn peer_count(&self) -> usize {
        self.routing_table.len()
    }
}
