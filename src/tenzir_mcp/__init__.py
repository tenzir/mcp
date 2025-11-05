"""Tenzir MCP Server."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, cast

PACKAGE_NAME = "tenzir-mcp"


def _read_pyproject() -> Mapping[str, Any]:
    import tomllib

    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        return cast(Mapping[str, Any], tomllib.load(pyproject_file))


def _load_project_metadata() -> dict[str, str]:
    try:
        metadata_mapping: Mapping[str, str] = cast(
            Mapping[str, str],
            importlib_metadata.metadata(PACKAGE_NAME),
        )
    except importlib_metadata.PackageNotFoundError:
        project_data = cast(
            Mapping[str, Any],
            _read_pyproject().get("project", {}),
        )

        def _collect_people(entries: Any) -> tuple[str, str]:
            if not isinstance(entries, list):
                return "", ""

            names: list[str] = []
            emails: list[str] = []

            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                if "name" in entry:
                    names.append(cast(str, entry["name"]))
                if "email" in entry:
                    emails.append(cast(str, entry["email"]))

            return ", ".join(names), ", ".join(emails)

        authors_names, authors_emails = _collect_people(
            project_data.get("authors", []),
        )
        maint_names, maint_emails = _collect_people(
            project_data.get("maintainers", []),
        )

        license_field = project_data.get("license", "")
        if isinstance(license_field, Mapping):
            license_text = cast(str, license_field.get("text", ""))
        elif isinstance(license_field, str):
            license_text = license_field
        else:
            license_text = ""

        return {
            "name": cast(str, project_data.get("name", PACKAGE_NAME)),
            "version": cast(str, project_data.get("version", "")),
            "description": cast(str, project_data.get("description", "")),
            "author": authors_names,
            "author_email": authors_emails,
            "maintainer": maint_names,
            "maintainer_email": maint_emails,
            "license": license_text,
        }

    return {
        "name": metadata_mapping.get("Name", PACKAGE_NAME) or PACKAGE_NAME,
        "version": metadata_mapping.get("Version", "") or "",
        "description": metadata_mapping.get("Summary", "") or "",
        "author": metadata_mapping.get("Author", "") or "",
        "author_email": metadata_mapping.get("Author-email", "") or "",
        "maintainer": metadata_mapping.get("Maintainer", "") or "",
        "maintainer_email": metadata_mapping.get("Maintainer-email", "") or "",
        "license": metadata_mapping.get("License", "") or "",
    }


_PROJECT_METADATA = _load_project_metadata()

__title__ = _PROJECT_METADATA["name"]
__version__ = _PROJECT_METADATA["version"]
__description__ = _PROJECT_METADATA["description"]
__author__ = _PROJECT_METADATA["author"]
__author_email__ = _PROJECT_METADATA["author_email"]
__maintainer__ = _PROJECT_METADATA["maintainer"]
__maintainer_email__ = _PROJECT_METADATA["maintainer_email"]
__license__ = _PROJECT_METADATA["license"]

__all__ = [
    "__title__",
    "__version__",
    "__description__",
    "__author__",
    "__author_email__",
    "__maintainer__",
    "__maintainer_email__",
    "__license__",
]
