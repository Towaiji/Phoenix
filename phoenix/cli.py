import sys
import ast
import subprocess
import hashlib
import shutil
from pathlib import Path

from phoenix.checker import check_types
from phoenix.errors import PhoenixError, PhoenixErrors
from phoenix.module_loader import annotate_source, resolve_imports
from phoenix.transpiler import transpile

__version__ = "0.1.0"

CACHE_DIR = Path(".phoenix_cache")
CACHE_DIR.mkdir(exist_ok=True)


def hash_source(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _find_compiler():
    for compiler in ("gcc", "cc", "clang"):
        if shutil.which(compiler):
            return compiler
    return None


def main():
    if len(sys.argv) == 2 and sys.argv[1] in {"--version", "-V"}:
        print(f"phoenix {__version__}")
        return

    if len(sys.argv) == 2:
        mode = "run"
        filename = sys.argv[1]
    elif len(sys.argv) == 3 and sys.argv[1] in {"check", "build"}:
        mode = sys.argv[1]
        filename = sys.argv[2]
    else:
        print("Usage:")
        print("  phoenix <file.py>")
        print("  phoenix check <file.py>   # analysis only, no compilation")
        print("  phoenix build <file.py>   # force transpile + compile")
        print("  phoenix --version")
        sys.exit(1)

    compiler = _find_compiler()
    if mode != "check" and compiler is None:
        print("❌ PhoenixError [Backend]: no C compiler found.")
        print("  help: Install gcc or clang (e.g. `sudo apt install gcc` or `brew install gcc`)")
        sys.exit(1)

    try:
        # ---- read source ----
        with open(filename, "r") as f:
            source = f.read()
            lines = source.splitlines()

        # ---- compute cache key ----
        src_hash = hash_source(source)
        cached_bin = CACHE_DIR / f"{src_hash}.bin"

        # ---- cache hit ----
        if mode == "run" and cached_bin.exists():
            shutil.copyfile(cached_bin, "output")
            print("✓ Using cached binary")
            return

        # ---- parse + check ----
        tree = ast.parse(source)
        annotate_source(tree, filename, lines)
        tree, import_errors = resolve_imports(tree, filename, lines, Path(filename).parent)
        if import_errors:
            raise PhoenixErrors(import_errors)
        type_ctx = check_types(tree, filename, lines)

        if mode == "check":
            print("✓ Phoenix approved. Code is type-stable.")
            return

        # ---- transpile ----
        c_code = transpile(tree, type_ctx)

        with open("output.c", "w") as f:
            f.write(c_code)

        # ---- compile ----
        subprocess.run(
            [compiler, "output.c", "-O3", "-o", "output"],
            check=True
        )

        # ---- store in cache ----
        shutil.copyfile("output", cached_bin)

        print("✓ Compiled to native binary: ./output")
        print("✓ Phoenix approved. Code is type-stable.")

    except PhoenixErrors as e:
        print(e.pretty())
        sys.exit(1)

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
