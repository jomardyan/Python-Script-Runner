#!/usr/bin/env python3
"""
CPU-Intensive Test Suite for Python Script Runner
Stress tests CPU performance with multiple computational benchmarks
"""

import time
import sys
import math
import random

# ANSI color
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_primes():
    """Prime number computation - heavy CPU"""
    print(f"{YELLOW}Test 1: Prime Numbers (up to 50,000){RESET}")
    start = time.time()
    
    def is_prime(n):
        if n <= 1: return False
        if n <= 3: return True
        if n % 2 == 0 or n % 3 == 0: return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0: return False
            i += 6
        return True
    
    primes = [i for i in range(2, 50000) if is_prime(i)]
    elapsed = time.time() - start
    print(f"  Found {len(primes):,} primes in {elapsed:.3f}s\n")
    return elapsed

def test_fibonacci():
    """Fibonacci recursive calculation - CPU intensive"""
    print(f"{YELLOW}Test 2: Fibonacci Sequence (recursive){RESET}")
    start = time.time()
    
    def fib(n):
        if n <= 1: return n
        return fib(n-1) + fib(n-2)
    
    results = [fib(i) for i in range(30, 36)]
    elapsed = time.time() - start
    print(f"  Computed {len(results)} Fibonacci numbers in {elapsed:.3f}s\n")
    return elapsed

def test_trigonometric():
    """Trigonometric functions - heavy math"""
    print(f"{YELLOW}Test 3: Trigonometric Functions (10M iterations){RESET}")
    start = time.time()
    
    result = 0
    for i in range(10000000):
        result += math.sin(i) * math.cos(i) * math.tan(i % 1000 / 1000)
    
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.3f}s, result={result:.2f}\n")
    return elapsed

def test_matrix_operations():
    """Matrix multiplication - CPU bound"""
    print(f"{YELLOW}Test 4: Matrix Multiplication (80x80){RESET}")
    start = time.time()
    
    size = 80
    a = [[random.random() for _ in range(size)] for _ in range(size)]
    b = [[random.random() for _ in range(size)] for _ in range(size)]
    c = [[0.0 for _ in range(size)] for _ in range(size)]
    
    for i in range(size):
        for j in range(size):
            for k in range(size):
                c[i][j] += a[i][k] * b[k][j]
    
    elapsed = time.time() - start
    result = sum(sum(row) for row in c)
    print(f"  Matrix ops completed in {elapsed:.3f}s, result={result:.2f}\n")
    return elapsed

def test_factorial():
    """Factorial calculations - heavy computation"""
    print(f"{YELLOW}Test 5: Factorial Calculations (10M iterations){RESET}")
    start = time.time()
    
    total = 0
    for i in range(10000000):
        total += math.factorial(i % 21)
    
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.3f}s, sum={total:,}\n")
    return elapsed

def test_pi_approximation():
    """Bailey–Borwein–Plouffe formula for Pi - intensive"""
    print(f"{YELLOW}Test 6: Pi Approximation (Machin Formula){RESET}")
    start = time.time()
    
    def arctan(x, num_terms=500):
        power = x
        result = power
        for i in range(1, num_terms):
            power *= -x * x
            result += power / (2 * i + 1)
        return result
    
    pi = 4 * (4 * arctan(1/5, 1000) - arctan(1/239, 1000))
    
    elapsed = time.time() - start
    print(f"  Pi approximation: {pi:.10f} in {elapsed:.3f}s\n")
    return elapsed

def test_sqrt_iterations():
    """Newton's method for square roots - intensive iterations"""
    print(f"{YELLOW}Test 7: Square Root Calculations (Newton's Method - 10M){RESET}")
    start = time.time()
    
    def sqrt_newton(n, iterations=100):
        x = n
        for _ in range(iterations):
            x = 0.5 * (x + n / x)
        return x
    
    results = [sqrt_newton(random.uniform(1, 1000)) for _ in range(10000)]
    
    elapsed = time.time() - start
    print(f"  Computed {len(results):,} square roots in {elapsed:.3f}s\n")
    return elapsed

def test_monte_carlo():
    """Monte Carlo Pi estimation - random heavy computation"""
    print(f"{YELLOW}Test 8: Monte Carlo Pi Estimation (50M samples){RESET}")
    start = time.time()
    
    inside = 0
    for _ in range(50000000):
        x = random.random()
        y = random.random()
        if x*x + y*y <= 1:
            inside += 1
    
    pi_estimate = 4 * inside / 50000000
    elapsed = time.time() - start
    print(f"  Pi estimate: {pi_estimate:.6f} in {elapsed:.3f}s\n")
    return elapsed

def test_collatz():
    """Collatz conjecture - iterative heavy"""
    print(f"{YELLOW}Test 9: Collatz Conjecture (1M sequences){RESET}")
    start = time.time()
    
    def collatz_length(n):
        length = 0
        while n != 1:
            if n % 2 == 0:
                n = n // 2
            else:
                n = 3 * n + 1
            length += 1
        return length
    
    lengths = [collatz_length(random.randint(1, 1000000)) for _ in range(1000000)]
    
    elapsed = time.time() - start
    avg_length = sum(lengths) / len(lengths)
    print(f"  Processed {len(lengths):,} sequences, avg length={avg_length:.2f} in {elapsed:.3f}s\n")
    return elapsed

def test_sorting():
    """Complex sorting operations - memory and CPU"""
    print(f"{YELLOW}Test 10: Sorting Benchmarks (1M integers){RESET}")
    start = time.time()
    
    data = [random.randint(1, 1000000) for _ in range(1000000)]
    sorted_data = sorted(data)
    
    # Multiple passes
    for _ in range(2):
        sorted_data = sorted(sorted_data, reverse=True)
        sorted_data = sorted(sorted_data)
    
    elapsed = time.time() - start
    print(f"  Sorted 1M integers (3 passes) in {elapsed:.3f}s\n")
    return elapsed

def main():
    """Main execution"""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}CPU Stress Test Suite - Python Script Runner{RESET}")
    print(f"{YELLOW}{'='*60}\n{RESET}")
    
    try:
        times = []
        times.append(test_primes())
        times.append(test_fibonacci())
        times.append(test_trigonometric())
        times.append(test_matrix_operations())
        times.append(test_factorial())
        times.append(test_pi_approximation())
        times.append(test_sqrt_iterations())
        times.append(test_monte_carlo())
        times.append(test_collatz())
        times.append(test_sorting())
        
        total_time = sum(times)
        
        print(f"{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}All 10 CPU tests completed: {total_time:.3f}s total{RESET}")
        print(f"{YELLOW}{'='*60}\n{RESET}")
        
        sys.exit(0)
    
    except Exception as e:
        print(f"{YELLOW}ERROR: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
