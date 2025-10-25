#!/usr/bin/env python3
"""
Test Runner for Trading System
Runs all tests and generates a coverage report
"""

import sys
import os
import subprocess


def run_all_tests():
    """Run all tests with pytest"""
    print("=" * 80)
    print("TRADING SYSTEM TEST SUITE")
    print("=" * 80)
    print()
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed")
        print("Please run: pip install -r requirements.txt")
        return 1
    
    # Run pytest with verbose output and coverage
    test_args = [
        'tests/',
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
        '--color=yes',  # Colored output
    ]
    
    # Try to run with coverage if available
    try:
        import pytest_cov
        test_args.extend([
            '--cov=data',
            '--cov=signals',
            '--cov=backtests',
            '--cov=execution',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov'
        ])
        print("Running tests with coverage analysis...")
    except ImportError:
        print("Running tests without coverage (pytest-cov not installed)...")
    
    print()
    
    # Run the tests
    exit_code = pytest.main(test_args)
    
    print()
    print("=" * 80)
    
    if exit_code == 0:
        print("✓ ALL TESTS PASSED")
        print()
        if os.path.exists('htmlcov/index.html'):
            print(f"Coverage report generated: {os.path.abspath('htmlcov/index.html')}")
    else:
        print("✗ SOME TESTS FAILED")
        print(f"Exit code: {exit_code}")
    
    print("=" * 80)
    
    return exit_code


def run_specific_test_file(test_file):
    """Run a specific test file"""
    print(f"Running tests in {test_file}...")
    
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed")
        return 1
    
    exit_code = pytest.main([test_file, '-v', '--tb=short'])
    return exit_code


def run_specific_test(test_path):
    """Run a specific test (e.g., tests/test_signals.py::TestBreakoutSignals::test_name)"""
    print(f"Running test: {test_path}")
    
    try:
        import pytest
    except ImportError:
        print("ERROR: pytest not installed")
        return 1
    
    exit_code = pytest.main([test_path, '-v', '--tb=short'])
    return exit_code


def list_tests():
    """List all available tests"""
    print("Available test files:")
    print()
    
    tests_dir = os.path.join(os.path.dirname(__file__), 'tests')
    
    if not os.path.exists(tests_dir):
        print(f"Tests directory not found: {tests_dir}")
        return
    
    test_files = [f for f in os.listdir(tests_dir) if f.startswith('test_') and f.endswith('.py')]
    
    for test_file in sorted(test_files):
        print(f"  - {test_file}")
    
    print()
    print("To run a specific test file:")
    print("  python3 run_tests.py tests/test_signals.py")
    print()
    print("To run all tests:")
    print("  python3 run_tests.py")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        
        if arg in ['-h', '--help']:
            print("Trading System Test Runner")
            print()
            print("Usage:")
            print("  python3 run_tests.py                    # Run all tests")
            print("  python3 run_tests.py --list             # List all test files")
            print("  python3 run_tests.py tests/test_*.py    # Run specific test file")
            print("  python3 run_tests.py tests/test_*.py::TestClass::test_method  # Run specific test")
            print()
            return 0
        
        elif arg == '--list':
            list_tests()
            return 0
        
        elif arg.endswith('.py'):
            # Run specific test file
            return run_specific_test_file(arg)
        
        elif '::' in arg:
            # Run specific test
            return run_specific_test(arg)
        
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information")
            return 1
    
    else:
        # Run all tests
        return run_all_tests()


if __name__ == '__main__':
    sys.exit(main())
