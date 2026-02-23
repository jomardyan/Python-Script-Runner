#!/usr/bin/env python3
"""
Test script to demonstrate the visualization feature.

This script performs various operations to showcase the execution flow
visualization including computation, I/O operations, and resource usage.
"""

import time
import sys
import io

# Ensure UTF-8 output encoding on all platforms (including Windows)
if sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

def compute_fibonacci(n):
    """Compute fibonacci numbers to stress CPU."""
    if n <= 1:
        return n
    return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)

def main():
    print("Starting test script execution...")
    print(f"Python version: {sys.version}")

    # Phase 1: Simple computation
    print("\nPhase 1: Computing fibonacci numbers...")
    for i in range(5):
        result = compute_fibonacci(20)
        print(f"  fib(20) = {result}")

    # Phase 2: Memory allocation
    print("\nPhase 2: Allocating memory...")
    data = []
    for i in range(1000):
        data.append([0] * 1000)
    print(f"  Allocated {len(data)} arrays")

    # Phase 3: Sleep to show monitoring
    print("\nPhase 3: Simulating long-running operation...")
    time.sleep(2)
    print("  Operation completed")

    # Phase 4: Cleanup
    print("\nPhase 4: Cleanup...")
    data.clear()
    print("  Cleanup complete")

    print("\n✅ Test script completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
