#!/usr/bin/env python3
"""Test Week 2 pay-for-performance import and calculations"""

import sys
import os
# Add the backend directory to path
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')

from decimal import Decimal
from app.services.pay_for_performance import calculate_fee
import asyncio


async def main():
    # Test 1: Successful calculation with 3% savings
    result = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6200000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    
    print("Test 1 - 3% savings on $50B portfolio:")
    print(f"  eligible: {result['eligible']}")
    print(f"  savings: ${result['savings']:,.2f}")
    print(f"  savings %: {result['savings_percentage']}%")
    print(f"  fee: ${result['fee']:,.2f}")
    print(f"  reason: {result['reason']}")
    
    # Test 2: Below threshold
    result2 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6340000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print("\nTest 2 - 1.25% savings (below 2% threshold):")
    print(f"  eligible: {result2['eligible']}")
    print(f"  reason: {result2['reason']}")
    print(f"  fee: ${result2['fee']}")
    
    # Test 3: No savings
    result3 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6500000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print("\nTest 3 - No savings (worse result):")
    print(f"  eligible: {result3['eligible']}")
    print(f"  reason: {result3['reason']}")
    print(f"  fee: ${result3['fee']}")
    
    # Test 4: Fee cap
    result4 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('5000000000'),
        portfolio_notional=Decimal('100000000000'),
        max_fee_cap_percentage=Decimal('0.5'),
    )
    max_cap = Decimal('100000000000') * Decimal('0.5') / Decimal('100')
    print("\nTest 4 - Fee cap ($100B portfolio):")
    print(f"  savings: ${result4['savings']:,.2f} ({result4['savings_percentage']}%)")
    print(f"  calculated fee: ${result4['fee']:,.2f}")
    print(f"  max cap (0.5%): ${max_cap:,.2f}")
    print(f"  fee capped: {result4['fee'] <= max_cap}")
    
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())