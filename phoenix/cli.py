import sys
import ast
from phoenix.checker import check_types
from phoenix.errors import PhoenixError
from phoenix.transpiler import transpile
import subprocess
import tempfile
import os

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
        
        c_code = transpile(tree)
        
        with open("output.c", "w") as f:
            f.write(c_code)
            
        subprocess.run(["gcc", "output.c", "-o", "output"], check=True)
        
        print("✓ Compiled to native binary: ./output")
        
        print("✓ Phoenix approved. Code is type-stable.")

    except PhoenixError as e:
        print(e.pretty())
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
