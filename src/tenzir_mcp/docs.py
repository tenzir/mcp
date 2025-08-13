"""Access to bundled Tenzir documentation."""

import json
from pathlib import Path

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 compatibility
    from importlib_resources import files  # type: ignore


class DocsMetadata:
    """Metadata about the bundled documentation."""

    def __init__(self, metadata: dict[str, str]) -> None:
        self.commit_sha = metadata.get("commit_sha", "unknown")
        self.repository = metadata.get("repository", "https://github.com/tenzir/docs")
        self.download_timestamp = metadata.get("download_timestamp", "unknown")

    def __repr__(self) -> str:
        return f"DocsMetadata(commit_sha='{self.commit_sha[:8]}...', timestamp='{self.download_timestamp}')"


class TenzirDocs:
    """Access to bundled Tenzir documentation."""

    def __init__(self) -> None:
        self._docs_root: Path | None = None
        self._metadata: DocsMetadata | None = None

    @property
    def docs_root(self) -> Path:
        """Get the root directory of the bundled docs."""
        if self._docs_root is None:
            # First try fallback for development
            import tenzir_mcp

            pkg_root = Path(tenzir_mcp.__file__).parent
            potential_docs_path = pkg_root / "data" / "docs"

            if potential_docs_path.exists():
                self._docs_root = potential_docs_path
            else:
                try:
                    # Try to find docs in package data
                    docs_pkg = files("tenzir_mcp.data.docs")
                    if hasattr(docs_pkg, "_path"):
                        # For editable installs or direct path access
                        self._docs_root = docs_pkg._path
                    else:
                        # For wheel installs, we need to extract to a temp location
                        # This is a simplified approach - in practice you might want
                        # to cache this in a temp directory
                        raise NotImplementedError(
                            "Wheel-based docs access not yet implemented"
                        )
                except (ModuleNotFoundError, FileNotFoundError):
                    raise FileNotFoundError(
                        f"Documentation not found at {potential_docs_path}. "
                        "Run 'make update-docs' or rebuild the package."
                    ) from None

            if not self._docs_root.exists():
                raise FileNotFoundError(
                    f"Documentation not found at {self._docs_root}. "
                    "Run 'make update-docs' or rebuild the package."
                )

        return self._docs_root

    @property
    def metadata(self) -> DocsMetadata:
        """Get metadata about the bundled documentation."""
        if self._metadata is None:
            metadata_file = self.docs_root / ".metadata.json"
            if metadata_file.exists():
                with metadata_file.open("r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                self._metadata = DocsMetadata(metadata_dict)
            else:
                # Default metadata if file doesn't exist
                self._metadata = DocsMetadata({})

        return self._metadata

    def list_files(self, pattern: str = "**/*") -> list[Path]:
        """List all files in the docs matching the given pattern."""
        docs_root = self.docs_root
        return [p for p in docs_root.glob(pattern) if p.is_file()]

    def read_file(self, relative_path: str | Path) -> str:
        """Read a documentation file by its relative path."""
        file_path = self.docs_root / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {relative_path}")

        with file_path.open("r", encoding="utf-8") as f:
            return f.read()

    def find_files(self, name_pattern: str) -> list[Path]:
        """Find files by name pattern (e.g., '*.md', 'index.*')."""
        return [p for p in self.docs_root.rglob(name_pattern) if p.is_file()]

    def get_file_path(self, relative_path: str | Path) -> Path:
        """Get the absolute path to a documentation file."""
        file_path = self.docs_root / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {relative_path}")
        return file_path

    def exists(self, relative_path: str | Path) -> bool:
        """Check if a documentation file exists."""
        return (self.docs_root / relative_path).exists()


# Global instance for easy access
docs = TenzirDocs()


def get_docs() -> TenzirDocs:
    """Get the global TenzirDocs instance."""
    return docs


def read_doc_file(relative_path: str | Path) -> str:
    """Convenience function to read a documentation file."""
    return docs.read_file(relative_path)


def list_doc_files(pattern: str = "**/*") -> list[Path]:
    """Convenience function to list documentation files."""
    return docs.list_files(pattern)


def get_docs_metadata() -> DocsMetadata:
    """Convenience function to get documentation metadata."""
    return docs.metadata
