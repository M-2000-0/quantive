use std::collections::HashMap;

use omnichain_types::*;

/// Delegated Proof-of-Stake manager.
///
/// Handles stake delegation, validator election, and slashing.
pub struct DPoS {
    pub min_self_stake: Amount,
    pub max_validators: usize,
    pub epoch_length: u64,
    pub validators: HashMap<Address, ValidatorStake>,
    pub delegations: HashMap<Address, Vec<Delegation>>,
}

#[derive(Debug, Clone)]
pub struct ValidatorStake {
    pub address: Address,
    pub self_stake: Amount,
    pub total_delegated: Amount,
    pub commission: u16,
    pub status: ValidatorStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ValidatorStatus {
    Active,
    Jailed { until: Slot },
    Tombstoned,
}

#[derive(Debug, Clone)]
pub struct Delegation {
    pub delegator: Address,
    pub validator: Address,
    pub amount: Amount,
    pub active: bool,
}

impl DPoS {
    pub fn new(min_self_stake: Amount, max_validators: usize, epoch_length: u64) -> Self {
        Self {
            min_self_stake,
            max_validators,
            epoch_length,
            validators: HashMap::new(),
            delegations: HashMap::new(),
        }
    }

    /// Register a new validator with self-stake.
    pub fn register_validator(
        &mut self,
        address: Address,
        self_stake: Amount,
        commission: u16,
    ) -> Result<(), Error> {
        if self_stake < self.min_self_stake {
            return Err(Error::Other("Self-stake below minimum".into()));
        }
        if commission > 100 {
            return Err(Error::Other("Commission cannot exceed 100%".into()));
        }
        self.validators.insert(address, ValidatorStake {
            address,
            self_stake,
            total_delegated: 0,
            commission,
            status: ValidatorStatus::Active,
        });
        Ok(())
    }

    /// Delegate tokens to a validator.
    pub fn delegate(&mut self, delegator: Address, validator: Address, amount: Amount) -> Result<(), Error> {
        let stake = self.validators.get_mut(&validator)
            .ok_or_else(|| Error::Other("Validator not found".into()))?;
        stake.total_delegated += amount;

        self.delegations.entry(delegator)
            .or_default()
            .push(Delegation { delegator, validator, amount, active: true });
        Ok(())
    }

    /// Elect the active validator set for the next epoch.
    pub fn elect_validator_set(&self, epoch: Epoch) -> ValidatorSet {
        let active: Vec<Validator> = self.validators
            .iter()
            .filter(|(_, s)| s.status == ValidatorStatus::Active)
            .map(|(addr, s)| {
                let total = s.self_stake + s.total_delegated;
                Validator {
                    address: *addr,
                    public_key: [0u8; 32],
                    self_stake: s.self_stake,
                    delegated_stake: s.total_delegated,
                    commission_rate: s.commission,
                    endpoint: String::new(),
                    node_id: String::new(),
                    is_active: true,
                    jail_until: None,
                    total_stake: total,
                }
            })
            .collect();

        ValidatorSet::new(epoch, active, self.max_validators)
    }

    /// Slash a validator for misbehavior.
    pub fn slash(&mut self, address: &Address, penalty_pct: u8) -> Result<Amount, Error> {
        let stake = self.validators.get_mut(address)
            .ok_or_else(|| Error::Other("Validator not found".into()))?;

        let penalty = (stake.self_stake * penalty_pct as u128) / 100;
        stake.self_stake = stake.self_stake.saturating_sub(penalty);
        Ok(penalty)
    }

    /// Jail a validator (temporarily remove from active set).
    pub fn jail(&mut self, address: &Address, until: Slot) {
        if let Some(stake) = self.validators.get_mut(address) {
            stake.status = ValidatorStatus::Jailed { until };
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_validator() {
        let mut dpos = DPoS::new(100, 10, 100);
        let addr = [1u8; 20];
        assert!(dpos.register_validator(addr, 200, 10).is_ok());
        assert!(dpos.validators.contains_key(&addr));
    }

    #[test]
    fn test_register_validator_fails_below_min() {
        let mut dpos = DPoS::new(100, 10, 100);
        let addr = [1u8; 20];
        assert!(dpos.register_validator(addr, 50, 10).is_err());
    }

    #[test]
    fn test_delegate_increases_stake() {
        let mut dpos = DPoS::new(100, 10, 100);
        let val = [1u8; 20];
        let del = [2u8; 20];
        dpos.register_validator(val, 200, 10).unwrap();
        dpos.delegate(del, val, 500).unwrap();
        assert_eq!(dpos.validators[&val].total_delegated, 500);
    }

    #[test]
    fn test_slash_reduces_self_stake() {
        let mut dpos = DPoS::new(100, 10, 100);
        let addr = [1u8; 20];
        dpos.register_validator(addr, 1000, 10).unwrap();
        let penalty = dpos.slash(&addr, 10).unwrap();
        assert_eq!(penalty, 100);
        assert_eq!(dpos.validators[&addr].self_stake, 900);
    }

    #[test]
    fn test_jail_changes_status() {
        let mut dpos = DPoS::new(100, 10, 100);
        let addr = [1u8; 20];
        dpos.register_validator(addr, 1000, 10).unwrap();
        dpos.jail(&addr, 100);
        assert_eq!(dpos.validators[&addr].status, ValidatorStatus::Jailed { until: 100 });
    }

    #[test]
    fn test_elect_excludes_jailed() {
        let mut dpos = DPoS::new(100, 10, 100);
        dpos.register_validator([1u8; 20], 1000, 10).unwrap();
        dpos.register_validator([2u8; 20], 1000, 10).unwrap();
        dpos.jail(&[2u8; 20], 999);
        let set = dpos.elect_validator_set(1);
        assert_eq!(set.len(), 1);
        assert_eq!(set.validators[0].address, [1u8; 20]);
    }
}
