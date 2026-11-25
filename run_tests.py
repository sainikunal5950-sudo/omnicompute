"""Test runner for OmniCompute modules: python run_tests.py <module_number>"""
import glob
import subprocess
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <module_number> [extra_pytest_args...]")
        sys.exit(1)

    module_num = sys.argv[1]
    pattern = f"tests/test_m{module_num}_*.py"
    matching_files = glob.glob(pattern)

    if not matching_files:
        print(f"Error: No test files found matching pattern '{pattern}'")
        sys.exit(1)

    cmd = [sys.executable, "-m", "pytest", "-v"] + matching_files + sys.argv[2:]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()

