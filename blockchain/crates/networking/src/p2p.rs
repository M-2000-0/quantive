use std::collections::HashSet;
use std::sync::Arc;

use libp2p::{
    identity,
    swarm::{Swarm, Config as SwarmConfig, NetworkBehaviour},
    Multiaddr, PeerId, Transport,
};
use libp2p::core::upgrade;
use libp2p_kad::{Behaviour as KadBehaviour, Config as KadConfig, store::MemoryStore};
use libp2p_gossipsub::{Behaviour as GossipSubBehaviour, ConfigBuilder, MessageAuthenticity, MessageId, IdentTopic};
use libp2p::tcp::tokio::Transport as TcpTransport;
use libp2p::noise;
use libp2p::yamux;
use parking_lot::RwLock;
use sha3::Digest;

use omnichain_types::*;

pub struct P2PNetwork {
    pub peer_id: PeerId,
    pub swarm: Option<Swarm<NodeBehaviour>>,
    pub connected_peers: Arc<RwLock<HashSet<PeerId>>>,
    pub known_peers: Arc<RwLock<Vec<Multiaddr>>>,
}

#[derive(NetworkBehaviour)]
pub struct NodeBehaviour {
    pub gossipsub: GossipSubBehaviour,
    pub kademlia: KadBehaviour<MemoryStore>,
}

impl P2PNetwork {
    pub fn new(keypair: identity::Keypair) -> Result<Self, Error> {
        let peer_id = keypair.public().to_peer_id();

        let noise_config = noise::Config::new(&keypair)
            .map_err(|e| Error::Network(format!("Noise config: {}", e)))?;

        let transport = TcpTransport::default()
            .upgrade(upgrade::Version::V1)
            .authenticate(noise_config)
            .multiplex(yamux::Config::default())
            .boxed();

        let gossipsub_config = ConfigBuilder::default()
            .message_id_fn(|msg: &libp2p_gossipsub::Message| {
                let mut hasher = sha3::Sha3_256::new();
                hasher.update(&msg.data);
                MessageId::from(hasher.finalize().to_vec())
            })
            .build()
            .map_err(|e| Error::Network(format!("GossipSub config: {}", e)))?;

        let gossipsub = GossipSubBehaviour::new(
            MessageAuthenticity::Signed(keypair.clone()),
            gossipsub_config,
        )
        .map_err(|e| Error::Network(format!("GossipSub init: {}", e)))?;

        let store = MemoryStore::new(peer_id);
        let kademlia_config = KadConfig::new(libp2p_swarm::StreamProtocol::new("/omnichain/kad/1.0.0"));
        let kademlia = KadBehaviour::with_config(peer_id, store, kademlia_config);

        let behaviour = NodeBehaviour { gossipsub, kademlia };
        let config = SwarmConfig::with_tokio_executor();
        let swarm = Swarm::new(transport, behaviour, peer_id, config);

        Ok(Self {
            peer_id,
            swarm: Some(swarm),
            connected_peers: Arc::new(RwLock::new(HashSet::new())),
            known_peers: Arc::new(RwLock::new(Vec::new())),
        })
    }

    pub fn broadcast(&mut self, topic: &str, data: &[u8]) -> Result<(), Error> {
        if let Some(swarm) = self.swarm.as_mut() {
            let topic = IdentTopic::new(topic);
            swarm
                .behaviour_mut()
                .gossipsub
                .publish(topic, data.to_vec())
                .map_err(|e| Error::Network(format!("Publish: {}", e)))?;
        }
        Ok(())
    }

    pub fn subscribe(&mut self, topic: &str) -> Result<(), Error> {
        if let Some(swarm) = self.swarm.as_mut() {
            let topic = IdentTopic::new(topic);
            swarm
                .behaviour_mut()
                .gossipsub
                .subscribe(&topic)
                .map_err(|e| Error::Network(format!("Subscribe: {}", e)))?;
        }
        Ok(())
    }

    pub fn dial(&mut self, addr: Multiaddr) -> Result<(), Error> {
        if let Some(swarm) = self.swarm.as_mut() {
            swarm
                .dial(addr.clone())
                .map_err(|e| Error::Network(format!("Dial: {}", e)))?;
            self.known_peers.write().push(addr);
        }
        Ok(())
    }

    pub fn connected_count(&self) -> usize {
        self.connected_peers.read().len()
    }
}
