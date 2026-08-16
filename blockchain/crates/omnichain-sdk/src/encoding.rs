use sha3::{Digest, Keccak256};
use omnichain_types::*;

/// Compute a cross-chain message payload hash.
pub fn compute_message_id(source: ChainId, dest: ChainId, nonce: u64) -> Hash {
    let mut hasher = sha3::Sha3_256::new();
    hasher.update(&source.to_le_bytes());
    hasher.update(&dest.to_le_bytes());
    hasher.update(&nonce.to_le_bytes());
    hasher.finalize().into()
}

/// Compute deployment address of a contract (CREATE semantics).
pub fn compute_contract_address(deployer: &Address, nonce: Nonce) -> Address {
    let mut hasher = Keccak256::new();
    hasher.update(alloy_rlp::encode(deployer.as_slice()));
    hasher.update(alloy_rlp::encode(nonce));
    let result: [u8; 32] = hasher.finalize().into();
    let mut addr = [0u8; 20];
    addr.copy_from_slice(&result[12..32]);
    addr
}

/// Simple ABI encoder for basic types.
pub mod abi {
    use sha3::{Digest, Keccak256};

    pub fn encode_uint256(value: u128) -> Vec<u8> {
        let mut buf = vec![0u8; 32];
        let bytes = value.to_be_bytes();
        buf[32 - bytes.len()..].copy_from_slice(&bytes);
        buf
    }

    pub fn encode_address(addr: &[u8; 20]) -> Vec<u8> {
        let mut buf = vec![0u8; 32];
        buf[12..32].copy_from_slice(addr);
        buf
    }

    pub fn encode_bool(val: bool) -> Vec<u8> {
        let mut buf = vec![0u8; 32];
        if val {
            buf[31] = 1;
        }
        buf
    }

    pub fn encode_function_selector(sig: &str) -> [u8; 4] {
        let mut hasher = Keccak256::new();
        hasher.update(sig.as_bytes());
        let result: [u8; 32] = hasher.finalize().into();
        let mut selector = [0u8; 4];
        selector.copy_from_slice(&result[..4]);
        selector
    }
}
