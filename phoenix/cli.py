import sys
import ast
from checker import check_types

def main():
    if len(sys.argv) != 2:
        print("Usage: python cli.py <file.py>")
        sys.exit(1)

    filename = sys.argv[1]
    print(f"checking {filename}...")

    try:
        with open(filename, "r") as f:
            source = f.read()

        tree = ast.parse(source)
        check_types(tree)

        print("✓ Phoenix approved. Code is type-stable.")

    except Exception as e:
        print(f"❌ PhoenixError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
