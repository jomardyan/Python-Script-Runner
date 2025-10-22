#!/usr/bin/env python3
"""Simple test script for runner"""

import time
import sys

print("Starting test...")
print("Running some computation...")

# Simulate some work
total = 0
for i in range(10000000):
    total += i

print(f"Computation done: {total}")
print("Test complete!")
sys.exit(0)
