"""Shared helper utilities for package management."""

import re
from pathlib import Path
from typing import Any

import yaml


def validate_package_dir(path: str | Path) -> dict[str, Any]:
    """
    Validate package directory and return package.yaml data.

    Args:
        path: Path to the package directory

    Returns:
        Dictionary containing package.yaml data or error

    Raises:
        ValueError: If package directory is invalid
    """
    pkg_path = Path(path)

    if not pkg_path.exists():
        raise ValueError(f"Package directory does not exist: {path}")

    if not pkg_path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    yaml_path = pkg_path / "package.yaml"
    if not yaml_path.exists():
        raise ValueError(
            f"package.yaml not found in {path}. Not a valid package directory."
        )

    try:
        return read_package_yaml(pkg_path)
    except Exception as e:
        raise ValueError(f"Failed to read package.yaml: {e}") from e


def generate_tree(path: Path, prefix: str = "", max_depth: int = 4) -> str:
    """
    Generate ASCII tree representation of directory structure.

    Args:
        path: Root directory path
        prefix: Prefix for current level (used in recursion)
        max_depth: Maximum depth to traverse

    Returns:
        ASCII tree string
    """
    if max_depth <= 0:
        return ""

    tree_lines = []

    try:
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    except PermissionError:
        return f"{prefix}[Permission Denied]\n"

    for idx, entry in enumerate(entries):
        is_last = idx == len(entries) - 1
        connector = "└── " if is_last else "├── "
        tree_lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            subtree = generate_tree(entry, prefix + extension, max_depth - 1)
            if subtree:
                tree_lines.append(subtree.rstrip("\n"))

    return "\n".join(tree_lines)


def read_package_yaml(path: Path) -> dict[str, Any]:
    """
    Read and parse package.yaml.

    Args:
        path: Package directory path

    Returns:
        Parsed package.yaml data
    """
    yaml_path = path / "package.yaml"
    with yaml_path.open("r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data


def write_package_yaml(path: Path, data: dict[str, Any]) -> None:
    """
    Write package.yaml with proper formatting.

    Args:
        path: Package directory path
        data: Package data to write
    """
    yaml_path = path / "package.yaml"
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from TQL test file.

    Args:
        content: File content with potential frontmatter

    Returns:
        Tuple of (metadata dict, remaining content)
    """
    # Check for YAML frontmatter (--- at start)
    if not content.startswith("---\n"):
        return {}, content

    # Find closing ---
    parts = content.split("\n---\n", 2)
    if len(parts) < 2:
        return {}, content

    try:
        metadata = yaml.safe_load(parts[1])
        body = parts[2] if len(parts) > 2 else ""
        return metadata or {}, body
    except yaml.YAMLError:
        return {}, content


def generate_frontmatter(metadata: dict[str, Any]) -> str:
    """
    Generate YAML frontmatter for test files.

    Args:
        metadata: Test metadata

    Returns:
        Formatted frontmatter string
    """
    if not metadata:
        return ""

    yaml_content = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_content}---\n"


def validate_package_id(package_id: str) -> bool:
    """
    Validate package ID format.

    Args:
        package_id: Package identifier

    Returns:
        True if valid, False otherwise
    """
    # Package IDs should be lowercase, alphanumeric with underscores/hyphens
    pattern = r"^[a-z][a-z0-9_-]*$"
    return bool(re.match(pattern, package_id))


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)
