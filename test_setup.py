"""
Test script to verify setup and dependencies.
"""
import sys
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported."""
    print("Testing imports...")
    
    required_packages = [
        'pandas',
        'numpy',
        'matplotlib',
        'requests',
        'dotenv',
        'loguru',
    ]
    
    optional_packages = [
        'talib',
        'yfinance',
        'nsepy',
        'vectorbt',
        'backtrader',
    ]
    
    failed = []
    
    # Test required packages
    print("\nRequired packages:")
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            failed.append(package)
    
    # Test optional packages
    print("\nOptional packages:")
    for package in optional_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ⚠ {package} - Not installed (optional)")
    
    if failed:
        print(f"\nERROR: Missing required packages: {', '.join(failed)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def test_directories():
    """Test if required directories exist."""
    print("\nTesting directories...")
    
    required_dirs = [
        'config',
        'utils',
        'strategies',
        'backtesting',
        'data',
        'logs',
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ - MISSING")
            all_exist = False
    
    return all_exist

def test_config():
    """Test configuration files."""
    print("\nTesting configuration...")
    
    config_file = Path("config/config.py")
    env_example = Path("config/.env.example")
    env_file = Path("config/.env")
    
    if config_file.exists():
        print("  ✓ config/config.py")
    else:
        print("  ✗ config/config.py - MISSING")
        return False
    
    if env_example.exists():
        print("  ✓ config/.env.example")
    else:
        print("  ✗ config/.env.example - MISSING")
        return False
    
    if env_file.exists():
        print("  ✓ config/.env (exists)")
    else:
        print("  ⚠ config/.env - Not found (create from .env.example)")
    
    return True

def test_modules():
    """Test if main modules can be imported."""
    print("\nTesting modules...")
    
    modules = [
        'utils.logger',
        'utils.auth',
        'utils.market_data',
        'utils.indicators',
        'strategies.multi_indicator_strategy',
        'backtesting.backtest_engine',
    ]
    
    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except Exception as e:
            print(f"  ✗ {module} - ERROR: {e}")
            failed.append(module)
    
    return len(failed) == 0

def main():
    """Run all tests."""
    print("=" * 50)
    print("Trading Bot Setup Test")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Directories", test_directories()))
    results.append(("Configuration", test_config()))
    results.append(("Modules", test_modules()))
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n✓ All tests passed! Setup is complete.")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
