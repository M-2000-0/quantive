use std::net::SocketAddr;
use std::sync::Arc;

use anyhow::{Context, Result};
use tokio::signal;
use tracing::info;

use omnichain_types::*;
use omnichain_node::CliArgs;
use omnichain_node::JsonRpcServer;
use omnichain_storage::ChainStorage;
use omnichain_consensus::{ConsensusEngine, ConsensusConfig, DPoS};
use omnichain_execution::ExecutionEngine;
use omnichain_crosschain::{OMP, LightClient};

fn build_genesis_block(chain_id: ChainId) -> Block {
    Block {
        header: BlockHeader {
            version: 1,
            height: 0,
            slot: 0,
            epoch: 0,
            parent_hash: [0u8; 32],
            state_root: [0u8; 32],
            transactions_root: [0u8; 32],
            receipts_root: [0u8; 32],
            crosschain_messages_root: [0u8; 32],
            validator_set_hash: [0u8; 32],
            proposer: [0u8; 20],
            timestamp: 0,
            gas_used: 0,
            gas_limit: 30_000_000,
            extras: chain_id.to_le_bytes().to_vec(),
            block_type: BlockType::Genesis,
        },
        body: BlockBody {
            transactions: vec![],
            crosschain_messages: vec![],
        },
        signature: vec![],
    }
}

fn init_genesis(storage: &ChainStorage, chain_id: ChainId) -> Result<Block> {
    let genesis = build_genesis_block(chain_id);
    let hash = genesis.compute_hash();

    storage.store_block(&genesis)?;
    storage.store_state_root(&genesis.header.state_root)?;

    let hash_hex: String = hash.iter().map(|b| format!("{:02x}", b)).collect();
    info!("Genesis block created: height=0 hash={}", hash_hex);
    Ok(genesis)
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = CliArgs::parse_and_init();

    let storage = Arc::new(ChainStorage::open(&args.data_dir)
        .context("Failed to open storage")?);

    let genesis = match storage.latest_block()? {
        Some(b) => {
            info!("Chain state found at height {}", b.header.height);
            b
        }
        None => init_genesis(&storage, args.chain_id)?,
    };

    let _execution = ExecutionEngine::new(4, args.chain_id);
    let _dpos = DPoS::new(1_000_000_000_000, 100, 100);
    let consensus_config = ConsensusConfig {
        block_time_ms: 5000,
        pipeline_depth: 4,
        max_validators: 100,
        min_self_stake: 1_000_000_000_000,
        epoch_length_slots: 100,
    };
    let validators = ValidatorSet::new(0, vec![], 100);
    let _consensus = ConsensusEngine::new(consensus_config, validators);
    let _omp = OMP::new();
    let _light_client = LightClient::new(
        args.chain_id,
        genesis.header.clone(),
        ValidatorSet::new(0, vec![], 100),
    );

    if !args.validator_key.is_empty() && args.validator {
        info!("Validator mode enabled — key provided, engine ready");
    }

    let rpc_addr: SocketAddr = ([127, 0, 0, 1], args.rpc_port).into();
    let server = JsonRpcServer::new(rpc_addr, args.chain_id);

    let server_handle = tokio::spawn(async move {
        if let Err(e) = server.start().await {
            eprintln!("JSON-RPC server error: {}", e);
        }
    });

    signal::ctrl_c().await?;
    info!("Shutdown signal received, stopping node...");

    server_handle.abort();
    info!("Node stopped gracefully");
    Ok(())
}
