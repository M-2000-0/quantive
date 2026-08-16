use omnichain_types::*;

/// Build and sign transactions.
pub struct TransactionBuilder {
    pub nonce: Nonce,
    pub sender: Address,
    pub gas_limit: GasUnits,
    pub max_fee_per_gas: Amount,
    pub max_priority_fee: Amount,
    pub chain_id: ChainId,
}

impl TransactionBuilder {
    pub fn new(sender: Address, chain_id: ChainId) -> Self {
        Self {
            nonce: 0,
            sender,
            gas_limit: 21000,
            max_fee_per_gas: 1_000_000_000,
            max_priority_fee: 0,
            chain_id,
        }
    }

    pub fn nonce(mut self, nonce: Nonce) -> Self {
        self.nonce = nonce;
        self
    }

    pub fn gas_limit(mut self, limit: GasUnits) -> Self {
        self.gas_limit = limit;
        self
    }

    pub fn max_fee(mut self, fee: Amount) -> Self {
        self.max_fee_per_gas = fee;
        self
    }

    pub fn build_transfer(self, _to: Address, _value: Amount) -> Transaction {
        Transaction {
            nonce: self.nonce,
            sender: self.sender,
            gas_limit: self.gas_limit,
            max_fee_per_gas: self.max_fee_per_gas,
            max_priority_fee: self.max_priority_fee,
            chain_id: self.chain_id,
            tx_type: TransactionType::NativeTransfer,
            signature: Vec::new(),
            hash: [0u8; 32],
        }
    }

    pub fn build_contract_call(
        self,
        to: Address,
        data: Vec<u8>,
        value: Amount,
    ) -> Transaction {
        Transaction {
            nonce: self.nonce,
            sender: self.sender,
            gas_limit: self.gas_limit,
            max_fee_per_gas: self.max_fee_per_gas,
            max_priority_fee: self.max_priority_fee,
            chain_id: self.chain_id,
            tx_type: TransactionType::EVMCall { to, data, value },
            signature: Vec::new(),
            hash: [0u8; 32],
        }
    }

    pub fn build_deploy(self, code: Vec<u8>, value: Amount) -> Transaction {
        Transaction {
            nonce: self.nonce,
            sender: self.sender,
            gas_limit: 100_000,
            max_fee_per_gas: self.max_fee_per_gas,
            max_priority_fee: self.max_priority_fee,
            chain_id: self.chain_id,
            tx_type: TransactionType::ContractDeploy { code, value },
            signature: Vec::new(),
            hash: [0u8; 32],
        }
    }

    pub fn build_cross_chain_message(
        self,
        dest_chain: ChainId,
        payload: Vec<u8>,
    ) -> Transaction {
        Transaction {
            nonce: self.nonce,
            sender: self.sender,
            gas_limit: 50_000,
            max_fee_per_gas: self.max_fee_per_gas,
            max_priority_fee: self.max_priority_fee,
            chain_id: self.chain_id,
            tx_type: TransactionType::CrossChainMessage {
                dest_chain,
                dest_contract: Vec::new(),
                payload,
                gas_limit: 50_000,
            },
            signature: Vec::new(),
            hash: [0u8; 32],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_build_transfer() {
        let sender = [1u8; 20];
        let tx = TransactionBuilder::new(sender, 1)
            .nonce(0)
            .gas_limit(21000)
            .build_transfer([2u8; 20], 1000);
        assert_eq!(tx.sender, sender);
        assert_eq!(tx.chain_id, 1);
        assert_eq!(tx.tx_type, TransactionType::NativeTransfer);
    }

    #[test]
    fn test_build_contract_call() {
        let tx = TransactionBuilder::new([1u8; 20], 1)
            .build_contract_call([2u8; 20], vec![0x60, 0x00], 0);
        match tx.tx_type {
            TransactionType::EVMCall { to, data, value } => {
                assert_eq!(to, [2u8; 20]);
                assert_eq!(data, vec![0x60, 0x00]);
                assert_eq!(value, 0);
            }
            _ => panic!("Expected EVMCall"),
        }
    }

    #[test]
    fn test_build_deploy() {
        let tx = TransactionBuilder::new([1u8; 20], 1)
            .build_deploy(vec![0x60, 0x00], 100);
        match tx.tx_type {
            TransactionType::ContractDeploy { code, value } => {
                assert_eq!(code, vec![0x60, 0x00]);
                assert_eq!(value, 100);
            }
            _ => panic!("Expected ContractDeploy"),
        }
    }

    #[test]
    fn test_build_cross_chain_message() {
        let tx = TransactionBuilder::new([1u8; 20], 1)
            .build_cross_chain_message(2, b"payload".to_vec());
        match &tx.tx_type {
            TransactionType::CrossChainMessage { dest_chain, payload, .. } => {
                assert_eq!(*dest_chain, 2);
                assert_eq!(payload, b"payload");
            }
            _ => panic!("Expected CrossChainMessage"),
        }
    }
}
