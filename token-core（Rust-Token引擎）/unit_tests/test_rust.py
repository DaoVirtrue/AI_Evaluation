"""Unit tests for token-core Rust library (via cargo test)"""
import subprocess
import sys

def run_cargo_test():
    """Run Rust unit tests"""
    result = subprocess.run(
        ["cargo", "test", "--release"],
        capture_output=True, text=True, timeout=120
    )
    passed = result.returncode == 0
    output = result.stdout + "\n" + result.stderr
    return passed, output


if __name__ == "__main__":
    passed, output = run_cargo_test()
    if passed:
        print("[PASS] cargo test")
    else:
        print("[FAIL] cargo test")
        print(output)
    sys.exit(0 if passed else 1)
