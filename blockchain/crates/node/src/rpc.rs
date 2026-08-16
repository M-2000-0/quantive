use std::net::SocketAddr;

use jsonrpsee::server::{ServerBuilder, RpcModule};
use tracing::info;

use omnichain_types::*;

/// JSON-RPC server for Omnichain node.
pub struct JsonRpcServer {
    pub addr: SocketAddr,
    pub chain_id: ChainId,
}

impl JsonRpcServer {
    pub fn new(addr: SocketAddr, chain_id: ChainId) -> Self {
        Self { addr, chain_id }
    }

    pub async fn start(self) -> Result<(), Error> {
        let server = ServerBuilder::default()
            .build(&self.addr)
            .await
            .map_err(|e| Error::Other(format!("Failed to start JSON-RPC server: {}", e)))?;

        let mut module = RpcModule::new(());
        self.register_methods(&mut module);

        let _handle = server.start(module);
        info!("JSON-RPC server listening on {}", self.addr);
        Ok(())
    }

    fn register_methods(&self, module: &mut RpcModule<()>) {
        module
            .register_method("eth_blockNumber", |_, _ctx, _| {
                Ok::<String, jsonrpsee::types::ErrorObject>(format!("0x{:x}", 0u64))
            })
            .expect("Failed to register eth_blockNumber");

        module
            .register_method("eth_chainId", |_, _ctx, _| {
                Ok::<String, jsonrpsee::types::ErrorObject>(format!("0x{:x}", 1u64))
            })
            .expect("Failed to register eth_chainId");

        module
            .register_method("eth_gasPrice", |_, _ctx, _| {
                Ok::<String, jsonrpsee::types::ErrorObject>(format!("0x{:x}", 1_000_000_000u64))
            })
            .expect("Failed to register eth_gasPrice");

        module
            .register_method("eth_getBalance", |params, _ctx, _| {
                let _addr: String = params.one().unwrap_or_default();
                Ok::<String, jsonrpsee::types::ErrorObject>(format!("0x{:x}", 0u64))
            })
            .expect("Failed to register eth_getBalance");

        module
            .register_method("net_version", |_, _ctx, _| {
                Ok::<String, jsonrpsee::types::ErrorObject>("1".to_string())
            })
            .expect("Failed to register net_version");

        module
            .register_method("omni_getMessageStatus", |params, _ctx, _| {
                let _nonce: u64 = params.one().unwrap_or(0);
                Ok::<String, jsonrpsee::types::ErrorObject>("pending".to_string())
            })
            .expect("Failed to register omni_getMessageStatus");

        module
            .register_method("omni_getValidators", |params, _ctx, _| {
                let _epoch: u64 = params.one().unwrap_or(0);
                Ok::<String, jsonrpsee::types::ErrorObject>("[]".to_string())
            })
            .expect("Failed to register omni_getValidators");
    }
}
