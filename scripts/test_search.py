#!/usr/bin/env python3
"""Simple CLI utility to test documentation search."""

import argparse
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tenzir_mcp.tools.documentation.backends.sqlite import SQLiteSearchBackend


def main() -> None:
    parser = argparse.ArgumentParser(description="Test documentation search")
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=[
            "operator",
            "function",
            "tutorial",
            "guide",
            "explanation",
            "integration",
            "api",
            "mcp",
            "test",
            "changelog",
            "reference",
            "doc",
        ],
        help="Filter by document type",
    )
    args = parser.parse_args()

    # Create backend and search
    backend = SQLiteSearchBackend()
    doc_types = [args.type] if args.type else None
    results = backend.search(args.query, doc_types=doc_types, limit=args.limit)

    # Print results
    if not results:
        print(f'No results found for "{args.query}"')
        return

    print(f'Found {len(results)} result(s) for "{args.query}"\n')
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['path']}")
        print(f"   Title: {result['title']}")
        print(f"   Type: {result['type']}")
        if result.get("category"):
            print(f"   Category: {result['category']}")
        if result.get("example"):
            print(f"   Example: {result['example']}")
        print()


if __name__ == "__main__":
    main()
