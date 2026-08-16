use omnichain_types::*;
use ed25519_dalek::Signer;

/// Gossip topics used in the Omnichain network.
pub struct GossipTopics;

impl GossipTopics {
    pub const BLOCKS: &'static str = "omnichain/blocks";
    pub const TRANSACTIONS: &'static str = "omnichain/txs";
    pub const CROSS_CHAIN: &'static str = "omnichain/crosschain";
    pub const VALIDATOR_VOTES: &'static str = "omnichain/votes";
    pub const SNAPSHOTS: &'static str = "omnichain/snapshots";
}

#[derive(Debug, Clone)]
pub struct GossipMessage {
    pub topic: String,
    pub sender: Address,
    pub data: Vec<u8>,
    pub signature: Vec<u8>,
    pub timestamp: u64,
}

impl GossipMessage {
    pub fn new(topic: &str, data: Vec<u8>, private_key: &ed25519_dalek::SigningKey) -> Self {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let mut to_sign = Vec::new();
        to_sign.extend_from_slice(topic.as_bytes());
        to_sign.extend_from_slice(&data);
        to_sign.extend_from_slice(&timestamp.to_le_bytes());

        let signature = private_key.sign(&to_sign).to_bytes().to_vec();
        let sender: Address = {
            let pubkey = private_key.verifying_key();
            let encoded = pubkey.as_bytes();
            let mut addr = [0u8; 20];
            let len = encoded.len().min(20);
            addr[..len].copy_from_slice(&encoded[..len]);
            addr
        };

        Self {
            topic: topic.to_string(),
            sender,
            data,
            signature,
            timestamp,
        }
    }

    pub fn verify(&self, public_key: &ed25519_dalek::VerifyingKey) -> Result<bool, Error> {
        use ed25519_dalek::Signature;

        let mut msg = Vec::new();
        msg.extend_from_slice(self.topic.as_bytes());
        msg.extend_from_slice(&self.data);
        msg.extend_from_slice(&self.timestamp.to_le_bytes());

        let sig = Signature::from_slice(&self.signature)
            .map_err(|_| Error::InvalidSignature)?;

        Ok(public_key.verify_strict(&msg, &sig).is_ok())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::SigningKey;

    fn make_keypair() -> SigningKey {
        let mut seed = [0u8; 32];
        seed[0] = 1;
        SigningKey::from_bytes(&seed)
    }

    #[test]
    fn test_gossip_message_sign_and_verify() {
        let keypair = make_keypair();
        let msg = GossipMessage::new("test/topic", b"hello".to_vec(), &keypair);
        assert_eq!(msg.topic, "test/topic");
        assert_eq!(msg.data, b"hello");
        assert!(!msg.signature.is_empty());

        let pubkey = keypair.verifying_key();
        assert!(msg.verify(&pubkey).unwrap_or(false));
    }

    #[test]
    fn test_gossip_message_tampered() {
        let keypair = make_keypair();
        let mut msg = GossipMessage::new("test/topic", b"hello".to_vec(), &keypair);
        msg.data = b"tampered".to_vec();
        let pubkey = keypair.verifying_key();
        assert!(!msg.verify(&pubkey).unwrap_or(true));
    }
}
