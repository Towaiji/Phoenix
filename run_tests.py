import subprocess
import sys
from pathlib import Path

EXAMPLES_DIR = Path("examples")

EXPECTED_FAIL = {
    "bad_type.py",
    "bad_list.py",
    "bad_eval.py",
    "bad_exec.py",
    "bad_import.py",
    "bad_while.py",
    "bad_for_dynamic.py",
    "bad_big.py",
    "bench_python.py"
}

def run_test(file_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phoenix.cli",
            str(file_path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr

def main():
    passed = 0
    failed = 0

    for file in sorted(EXAMPLES_DIR.glob("*.py")):
        code, output = run_test(file)
        name = file.name

        if name in EXPECTED_FAIL:
            if code != 0:
                print(f"✓ {name} correctly rejected")
                passed += 1
            else:
                print(f"✗ {name} SHOULD have failed but passed")
                print(output)
                failed += 1
        else:
            if code == 0:
                print(f"✓ {name} correctly accepted")
                passed += 1
            else:
                print(f"✗ {name} SHOULD have passed but failed")
                print(output)
                failed += 1

    print("\nSummary:")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
