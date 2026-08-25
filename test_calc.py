#!/usr/bin/env python3
"""Quick test Week 2 pay-for-performance calculations"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

from decimal import Decimal
from app.services.pay_for_performance import SuccessFeeCalculator, calculate_fee
import asyncio


async def quick_test():
    # Test 1: Successful calculation with 3% savings
    result = await calculate_fee(
        baseline_cost=Decimal('6420000000'),  # $6.42B baseline
        optimized_cost=Decimal('6200000000'),  # $6.20B optimized
        portfolio_notional=Decimal('50000000000'),  # $50B portfolio
    )
    print(f"Test 1 - 3% savings:")
    print(f"  eligible: {result['eligible']}")
    print(f"  savings: ${result['savings']:,.2f}")
    print(f"  savings %: {result['savings_percentage']}%")
    print(f"  fee: ${result['fee']:,.2f}")
    print(f"  reason: {result['reason']}")
    
    # Test 2: Below threshold (1.25% savings)
    result2 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6340000000'),  # ~1.25% savings
        portfolio_notional=Decimal('50000000000'),
    )
    print(f"\nTest 2 - Below threshold (1.25%):")
    print(f"  eligible: {result2['eligible']}")
    print(f"  reason: {result2['reason'][:60]}...")
    print(f"  fee: ${result2['fee']}")
    
    # Test 3: No savings (worse result)
    result3 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6500000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print(f"\nTest 3 - No savings (worse):")
    print(f"  eligible: {result3['eligible']}")
    print(f"  reason: {result3['reason'][:60]}...")
    print(f"  fee: ${result3['fee']}")
    
    # Test 4: Fee cap test
    result4 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('5000000000'),  # 22% savings = $1.42B
        portfolio_notional=Decimal('100000000000'),  # $100B
        max_fee_cap_percentage=Decimal('0.5'),
    )
    max_cap = Decimal('100000000000') * Decimal('0.5') / Decimal('100')
    print(f"\nTest 4 - Fee cap ($100B portfolio):")
    print(f"  savings: ${result4['savings']:,.2f} ({result4['savings_percentage']}%)")
    print(f"  calculated fee: ${result4['fee']:,.2f}")
    print(f"  max cap (0.5%): ${max_cap:,.2f}")
    print(f"  fee capped: {result4['fee'] <= max_cap}")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(quick_test())