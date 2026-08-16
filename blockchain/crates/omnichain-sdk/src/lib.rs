//! Omnichain SDK — TypeScript-compatible helpers for building on Omnichain.
//!
//! This crate provides utilities for:
//! - Constructing and signing transactions
//! - Encoding/decoding cross-chain messages
//! - Computing addresses and hashes
//! - ABI encoding for EVM contracts

pub mod tx_builder;
pub mod encoding;
pub mod address;

pub use tx_builder::*;
pub use encoding::*;
pub use address::*;

