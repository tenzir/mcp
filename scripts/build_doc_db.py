#!/usr/bin/env python3
"""Build a SQLite FTS5 database from the documentation index."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from logging_utils import get_logger

logger = get_logger("build-doc-db")

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "src" / "tenzir_mcp" / "data" / "doc_index.json"
OUTPUT_PATH = REPO_ROOT / "src" / "tenzir_mcp" / "data" / "docs.db"


def build_database() -> None:
    """Build SQLite FTS5 database from the JSON index."""
    # Load the JSON index
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        index = json.load(f)

    # Remove existing database if present
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    # Create database connection
    conn = sqlite3.connect(OUTPUT_PATH)
    cursor = conn.cursor()

    # Create FTS5 virtual table with BM25 ranking
    # We'll index: path, title, name, category, and example
    cursor.execute("""
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            path UNINDEXED,
            title,
            name,
            category,
            example,
            type UNINDEXED,
            tokenize = 'porter ascii'
        )
    """)

    # Create a regular table to store see_also relationships
    cursor.execute("""
        CREATE TABLE see_also (
            doc_path TEXT NOT NULL,
            see_also_path TEXT NOT NULL,
            see_also_title TEXT NOT NULL,
            see_also_type TEXT NOT NULL,
            PRIMARY KEY (doc_path, see_also_path)
        )
    """)

    # Create index for faster lookups
    cursor.execute("""
        CREATE INDEX idx_see_also_doc_path ON see_also(doc_path)
    """)

    # Insert documents from all sections (avoiding duplicates)
    doc_count = 0
    link_count = 0
    inserted_paths: set[str] = set()

    for section in ["operators", "functions", "tutorials", "documents"]:
        section_data = index.get(section, {})
        for path, entry in section_data.items():
            # Skip if already inserted
            if path in inserted_paths:
                continue
            inserted_paths.add(path)

            # Determine document type
            doc_type = entry.get("type", section.rstrip("s"))

            # Insert into FTS5 table
            cursor.execute(
                """
                INSERT INTO docs_fts (path, title, name, category, example, type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    path,
                    entry.get("title", ""),
                    entry.get("name", ""),
                    entry.get("category", ""),
                    entry.get("example", ""),
                    doc_type,
                ),
            )
            doc_count += 1

            # Insert see_also relationships
            for see_also in entry.get("see_also", []):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO see_also (doc_path, see_also_path, see_also_title, see_also_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        path,
                        see_also.get("path", ""),
                        see_also.get("title", ""),
                        see_also.get("type", ""),
                    ),
                )
                link_count += 1

    # Create metadata table
    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Store metadata
    metadata = index.get("metadata", {})
    for key, value in metadata.items():
        cursor.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    conn.commit()
    conn.close()

# fmt: off
    logger.success(
        "built sqlite database with %s documents and %s cross-links",
        doc_count,
        link_count,
    )
    logger.info("database saved to %s", OUTPUT_PATH)
# fmt: on


if __name__ == "__main__":
    build_database()
