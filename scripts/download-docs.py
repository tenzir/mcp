#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "requests",
# ]
# ///

import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    from logging_utils import get_logger

    get_logger("download-docs").error("requests library not available — cannot download docs.")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from logging_utils import get_logger

logger = get_logger("download-docs")

# Configuration
DOCS_REPO = "https://api.github.com/repos/tenzir/docs"
DOWNLOAD_URL_TEMPLATE = "https://github.com/tenzir/docs/archive/{}.zip"
TIMEOUT = 30


def get_latest_commit_sha() -> str:
    """Get the latest commit SHA from the docs repository."""
    logger.info("fetching latest commit sha from tenzir/docs")

    # Use GitHub token if available (for CI)
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
        logger.info("using github token for authentication")

    try:
        response = requests.get(f"{DOCS_REPO}/commits/main", headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        commit_data = response.json()
        sha = commit_data["sha"]
        logger.success("latest commit sha: %s", sha[:8])
        return sha
    except requests.RequestException as e:
        logger.error("error fetching commit sha: %s", e)
        sys.exit(1)


def download_docs_archive(commit_sha: str) -> bytes:
    """Download the docs repository as a ZIP archive."""
    download_url = DOWNLOAD_URL_TEMPLATE.format(commit_sha)
    logger.info("downloading docs archive from %s", download_url)

    try:
        response = requests.get(download_url, timeout=TIMEOUT)
        response.raise_for_status()
        logger.success("downloaded %s bytes", len(response.content))
        return response.content
    except requests.RequestException as e:
        logger.error("error downloading docs archive: %s", e)
        sys.exit(1)


def get_docs_dir() -> Path:
    """Get the docs directory path and ensure parent directories exist."""
    script_dir = Path(__file__).parent
    docs_dir = script_dir.parent / "src" / "tenzir_mcp" / "data" / "docs"
    docs_dir.parent.mkdir(parents=True, exist_ok=True)
    return docs_dir


def extract_docs(archive_content: bytes, docs_dir: Path, commit_sha: str) -> None:
    """Extract docs from the ZIP archive to the target directory."""
    logger.info("extracting docs to %s", docs_dir)

    # Clean existing docs directory
    if docs_dir.exists():
        logger.info("cleaning existing docs directory")
        shutil.rmtree(docs_dir)

    # Define documentation file extensions to keep
    doc_extensions = {'.md', '.mdx', '.mdoc'}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_file = temp_path / "docs.zip"

        # Write archive to temporary file
        with zip_file.open("wb") as f:
            f.write(archive_content)

        # Extract archive
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(temp_path)

        # Find the extracted directory (should be docs-{sha})
        extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir() and d.name.startswith("docs-")]
        if not extracted_dirs:
            logger.error("could not find extracted docs directory")
            sys.exit(1)

        extracted_dir = extracted_dirs[0]
        logger.info("found extracted directory: %s", extracted_dir.name)

        # Copy only documentation files, preserving directory structure
        docs_dir.mkdir(parents=True, exist_ok=True)
        files_copied = 0

        for file_path in extracted_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in doc_extensions:
                rel_path = file_path.relative_to(extracted_dir)
                dest_path = docs_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                files_copied += 1

        logger.info("filtered extraction: kept %s documentation files (.md, .mdx, .mdoc)", files_copied)

    # Create a metadata file with commit info
    metadata = {
        "commit_sha": commit_sha,
        "repository": "https://github.com/tenzir/docs",
        "download_timestamp": datetime.now(timezone.utc).isoformat()
    }

    metadata_file = docs_dir / ".metadata.json"
    with metadata_file.open("w", encoding="utf-8") as f:
        __import__("json").dump(metadata, f, indent=2)

    logger.success("created metadata file: %s", metadata_file)


def count_files(directory: Path) -> int:
    """Count total files in directory recursively."""
    return sum(1 for _ in directory.rglob("*") if _.is_file())


def main() -> None:
    """Main function to download Tenzir documentation."""
    try:
        commit_sha = get_latest_commit_sha()
        archive_content = download_docs_archive(commit_sha)
        docs_dir = get_docs_dir()
        extract_docs(archive_content, docs_dir, commit_sha)

        file_count = count_files(docs_dir)
        logger.success("downloaded docs with %s files to %s", file_count, docs_dir)

    except KeyboardInterrupt:
        logger.warning("download cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error("unexpected error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
