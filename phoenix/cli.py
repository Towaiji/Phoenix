import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python cli.py <name>")
        sys.exit(1)
    
    name = sys.argv[1]
    print(f"checking {name}...")
    print("not implemented yet")
    
if __name__ == "__main__":
    main()
