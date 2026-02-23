#!/usr/bin/env python3
"""Simple sample script for Python Script Runner demonstration."""

import sys
import io

# Ensure UTF-8 output encoding on all platforms (including Windows)
if sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

print("Python Script Runner - Sample Script")
print("✅ Sample completed successfully")
print("\nThis script ran without errors!")

