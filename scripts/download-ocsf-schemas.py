#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "requests",
# ]
# ///

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict

import requests

# Configuration
SERVER = "https://schema.ocsf.io"
EXCLUDE_VERSIONS = ["1.0.0-rc.2", "1.0.0-rc.3"]
TIMEOUT = 10


def log(msg: str) -> None:
    """Log a message to stderr."""
    print(f"▶ {msg}", file=sys.stderr, flush=True)


def fetch_versions() -> list[str]:
    """Fetch available OCSF schema versions from the server."""
    log(f"Fetching available versions from {SERVER}")
    try:
        response = requests.get(SERVER, timeout=TIMEOUT)
        response.raise_for_status()
        body = response.content.decode()
        versions = sorted(
            version
            for version in re.findall("<option value=[^>]*>v([^<]*)</option>", body)
            if version not in EXCLUDE_VERSIONS
        )
        log(f"Found {len(versions)} versions: {', '.join(versions)}")
        return versions
    except requests.RequestException as e:
        log(f"Error fetching versions: {e}")
        sys.exit(1)


def download_schema(version: str) -> Dict[str, Any]:
    """Download the raw JSON schema for a specific version."""
    url = f"{SERVER}/{version}/export/schema"
    log(f"Downloading schema for version {version} from {url}")
    
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            log(f"Timeout on attempt {attempt + 1}/3 for version {version}")
            if attempt == 2:  # Last attempt
                raise
        except requests.RequestException as e:
            log(f"Error downloading schema for version {version}: {e}")
            raise


def get_data_dir() -> Path:
    """Get the data directory path and ensure it exists."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "src" / "tenzir_mcp" / "data" / "ocsf"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def save_schema(version: str, schema: Dict[str, Any], data_dir: Path) -> None:
    """Save the schema JSON to a file."""
    filename = f"{version}.json"
    filepath = data_dir / filename
    log(f"Saving schema to {filepath}")
    
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)


def main() -> None:
    """Main function to download all OCSF schemas."""
    versions = fetch_versions()
    data_dir = get_data_dir()
    
    # Clean up existing files
    log(f"Cleaning existing files in {data_dir}")
    for existing_file in data_dir.glob("*.json"):
        existing_file.unlink()
    
    # Download and save each version
    for version in versions:
        try:
            schema = download_schema(version)
            save_schema(version, schema, data_dir)
        except Exception as e:
            log(f"Failed to process version {version}: {e}")
            continue
    
    log(f"Successfully downloaded {len(list(data_dir.glob('*.json')))} schema files")


if __name__ == "__main__":
    main()