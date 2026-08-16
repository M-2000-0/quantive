use sha3::{Digest, Keccak256};
use omnichain_types::*;

/// Generate an Omnichain address from a public key.
pub fn address_from_public_key(public_key: &[u8]) -> Address {
    let mut hasher = Keccak256::new();
    hasher.update(public_key);
    let result: [u8; 32] = hasher.finalize().into();
    let mut addr = [0u8; 20];
    addr.copy_from_slice(&result[12..32]);
    addr
}

/// Checksum-encode an address per EIP-55.
pub fn checksum_encode(addr: &Address) -> String {
    let hex_str = hex::encode(addr);
    let mut hasher = Keccak256::new();
    hasher.update(hex_str.as_bytes());
    let hash: [u8; 32] = hasher.finalize().into();

    let mut result = String::with_capacity(42);
    result.push_str("0x");
    for (i, c) in hex_str.char_indices() {
        let hash_byte = hash[i / 2];
        let hash_nibble = if i % 2 == 0 {
            (hash_byte >> 4) & 0x0f
        } else {
            hash_byte & 0x0f
        };
        if hash_nibble >= 8 {
            result.push(c.to_ascii_uppercase());
        } else {
            result.push(c.to_ascii_lowercase());
        }
    }
    result
}

/// Validate a checksummed address.
pub fn validate_checksum(addr: &str) -> bool {
    if !addr.starts_with("0x") || addr.len() != 42 {
        return false;
    }
    let expected = checksum_encode(&hex::decode(&addr[2..]).unwrap_or_default().try_into().unwrap_or([0u8; 20]));
    addr == expected
}
