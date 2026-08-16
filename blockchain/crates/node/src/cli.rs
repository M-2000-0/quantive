use std::path::PathBuf;

use clap::Parser;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

/// Omnichain L1 Blockchain Node
#[derive(Parser, Debug)]
#[command(name = "omnichain-node")]
#[command(about = "Omnichain Layer 1 blockchain node", long_about = None)]
pub struct CliArgs {
    /// Data directory for chain state
    #[arg(short, long, default_value = "./data")]
    pub data_dir: PathBuf,

    /// P2P port
    #[arg(long, default_value = "30333")]
    pub p2p_port: u16,

    /// JSON-RPC port
    #[arg(long, default_value = "8545")]
    pub rpc_port: u16,

    /// Chain ID
    #[arg(long, default_value = "1")]
    pub chain_id: u64,

    /// Bootstrap node addresses (comma-separated)
    #[arg(long, default_value = "")]
    pub bootstraps: String,

    /// Validator private key (hex)
    #[arg(long, default_value = "")]
    pub validator_key: String,

    /// Enable validator mode
    #[arg(long, default_value = "false")]
    pub validator: bool,

    /// Log level
    #[arg(long, default_value = "info")]
    pub log_level: String,
}

impl CliArgs {
    pub fn parse_and_init() -> Self {
        let args = Self::parse();

        let level = match args.log_level.to_lowercase().as_str() {
            "trace" => Level::TRACE,
            "debug" => Level::DEBUG,
            "info" => Level::INFO,
            "warn" => Level::WARN,
            "error" => Level::ERROR,
            _ => Level::INFO,
        };

        let _ = FmtSubscriber::builder()
            .with_max_level(level)
            .with_target(true)
            .try_init();

        info!("Omnichain node starting...");
        info!("Data dir: {}", args.data_dir.display());
        info!("Chain ID: {}", args.chain_id);
        info!("P2P port: {}, RPC port: {}", args.p2p_port, args.rpc_port);

        args
    }
}
