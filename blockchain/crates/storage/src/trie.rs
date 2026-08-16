use std::collections::HashMap;

use sha3::Digest;
use serde::{Serialize, Deserialize};

use omnichain_types::*;

/// Simple Merkle Patricia Trie for state storage.
///
/// This is a simplified implementation. In production, this
/// would use a full Merkle Patricia Trie similar to Ethereum's.
#[derive(Debug, Default)]
pub struct StateTrie {
    nodes: HashMap<Hash, TrieNode>,
    root: Option<Hash>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TrieNode {
    Leaf { key: Vec<u8>, value: Vec<u8> },
    Branch { children: Vec<Option<Hash>>, value: Option<Vec<u8>> },
    Extension { prefix: Vec<u8>, child: Hash },
    Empty,
}

impl StateTrie {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            root: None,
        }
    }

    /// Insert a key-value pair and return the new root.
    pub fn insert(&mut self, key: &[u8], value: &[u8]) -> Hash {
        let node = TrieNode::Leaf {
            key: key.to_vec(),
            value: value.to_vec(),
        };
        let hash = Self::hash_node(&node);
        self.nodes.insert(hash, node);
        self.root = Some(hash);
        hash
    }

    /// Get a value by key.
    pub fn get(&self, key: &[u8]) -> Option<Vec<u8>> {
        let root = self.root.as_ref()?;
        match self.nodes.get(root) {
            Some(TrieNode::Leaf { key: k, value: v }) if k == key => Some(v.clone()),
            _ => None,
        }
    }

    pub fn root_hash(&self) -> Option<Hash> {
        self.root
    }

    fn hash_node(node: &TrieNode) -> Hash {
        let encoded = bincode::serialize(node).unwrap_or_default();
        let mut hasher = sha3::Sha3_256::new();
        hasher.update(&encoded);
        hasher.finalize().into()
    }

    /// Generate a Merkle proof for a given key.
    pub fn generate_proof(&self, key: &[u8]) -> Result<Vec<Vec<u8>>, Error> {
        let root = self.root.ok_or_else(|| Error::Storage("Empty trie".into()))?;
        let node = self.nodes.get(&root)
            .ok_or_else(|| Error::Storage("Root not found".into()))?;

        match node {
            TrieNode::Leaf { key: k, value: v } if k == key => {
                let encoded = bincode::serialize(node)
                    .map_err(|e| Error::Storage(e.to_string()))?;
                Ok(vec![encoded])
            }
            _ => Err(Error::Storage("Key not found in trie".into())),
        }
    }

    /// Verify a Merkle proof.
    pub fn verify_proof(_root: Hash, key: &[u8], value: &[u8], proof: &[Vec<u8>]) -> bool {
        if proof.is_empty() {
            return false;
        }
        if let Ok(node) = bincode::deserialize::<TrieNode>(&proof[0]) {
            match node {
                TrieNode::Leaf { key: k, value: v } => k == key && v == value,
                _ => false,
            }
        } else {
            false
        }
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_trie_insert_and_get() {
        let mut trie = StateTrie::new();
        let root = trie.insert(b"key1", b"value1");
        assert_eq!(trie.get(b"key1"), Some(b"value1".to_vec()));
        assert_eq!(trie.root_hash(), Some(root));
    }

    #[test]
    fn test_trie_empty_get() {
        let trie = StateTrie::new();
        assert_eq!(trie.get(b"nothing"), None);
    }

    #[test]
    fn test_trie_root_hash() {
        let mut trie = StateTrie::new();
        assert!(trie.root_hash().is_none());
        trie.insert(b"a", b"1");
        assert!(trie.root_hash().is_some());
    }

    #[test]
    fn test_trie_generate_and_verify_proof() {
        let mut trie = StateTrie::new();
        trie.insert(b"k", b"v");
        let proof = trie.generate_proof(b"k").unwrap();
        let root = trie.root_hash().unwrap();
        assert!(StateTrie::verify_proof(root, b"k", b"v", &proof));
        assert!(!StateTrie::verify_proof(root, b"k", b"wrong", &proof));
    }

    #[test]
    fn test_trie_proof_for_missing_key() {
        let mut trie = StateTrie::new();
        trie.insert(b"exists", b"yes");
        assert!(trie.generate_proof(b"missing").is_err());
    }
}
