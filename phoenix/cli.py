import sys
import ast
import subprocess
import hashlib
import shutil
from pathlib import Path

from phoenix.checker import check_types
from phoenix.errors import PhoenixError
from phoenix.transpiler import transpile


CACHE_DIR = Path(".phoenix_cache")
CACHE_DIR.mkdir(exist_ok=True)


def hash_source(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 -m phoenix.cli <file.py>")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        # ---- read source ----
        with open(filename, "r") as f:
            source = f.read()
            lines = source.splitlines()

        # ---- compute cache key ----
        src_hash = hash_source(source)
        cached_bin = CACHE_DIR / f"{src_hash}.bin"

        # ---- cache hit ----
        if cached_bin.exists():
            shutil.copyfile(cached_bin, "output")
            print("✓ Using cached binary")
            return

        # ---- parse + check ----
        tree = ast.parse(source)
        check_types(tree, filename, lines)

        # ---- transpile ----
        c_code = transpile(tree)

        with open("output.c", "w") as f:
            f.write(c_code)

        # ---- compile ----
        subprocess.run(
            ["gcc", "output.c", "-o", "output"],
            check=True
        )

        # ---- store in cache ----
        shutil.copyfile("output", cached_bin)

        print("✓ Compiled to native binary: ./output")
        print("✓ Phoenix approved. Code is type-stable.")

    except PhoenixError as e:
        print(e.pretty())
        sys.exit(1)

    except subprocess.CalledProcessError:
        print("❌ PhoenixError [Backend]: generated C code failed to compile.")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
