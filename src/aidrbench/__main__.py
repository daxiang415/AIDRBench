"""Allow ``python -m aidrbench`` execution."""

from aidrbench.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
