#!/usr/bin/env python3
"""Simple test Week 2: just pay_for_performance"""

import sys
import os
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')

from decimal import Decimal
from app.services.pay_for_performance import calculate_fee
import asyncio


async def main():
    # Test 1: Successful calculation
    result = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6200000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print(f"Test 1 - eligible: {result['eligible']}, fee: ${result['fee']:,.2f}")
    
    # Test 2: Below threshold
    result2 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6340000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print(f"Test 2 - eligible: {result2['eligible']}, reason: {result2['reason'][:40]}...")
    
    # Test 3: No savings
    result3 = await calculate_fee(
        baseline_cost=Decimal('6420000000'),
        optimized_cost=Decimal('6500000000'),
        portfolio_notional=Decimal('50000000000'),
    )
    print(f"Test 3 - eligible: {result3['eligible']}, fee: ${result3['fee']}")


asyncio.run(main())
print("\nSimple test completed successfully!")