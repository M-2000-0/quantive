use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("Invalid signature")]
    InvalidSignature,
    #[error("Insufficient balance")]
    InsufficientBalance,
    #[error("Nonce mismatch")]
    NonceMismatch,
    #[error("Invalid block: {0}")]
    InvalidBlock(String),
    #[error("Consensus error: {0}")]
    Consensus(String),
    #[error("Execution error: {0}")]
    Execution(String),
    #[error("Storage error: {0}")]
    Storage(String),
    #[error("Cross-chain error: {0}")]
    CrossChain(String),
    #[error("Network error: {0}")]
    Network(String),
    #[error("Serialization error: {0}")]
    Serialization(String),
    #[error("{0}")]
    Other(String),
}

impl From<Box<dyn std::error::Error>> for Error {
    fn from(e: Box<dyn std::error::Error>) -> Self {
        Error::Other(e.to_string())
    }
}
