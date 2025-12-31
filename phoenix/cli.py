import sys
import ast
from phoenix.checker import check_types
from phoenix.errors import PhoenixError

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 phoenix/cli.py <file.py>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, "r") as f:
            source = f.read()
            lines = source.splitlines()

        tree = ast.parse(source)
        check_types(tree, filename, lines)

        print("✓ Phoenix approved. Code is type-stable.")

    except PhoenixError as e:
        print(e.pretty())
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
