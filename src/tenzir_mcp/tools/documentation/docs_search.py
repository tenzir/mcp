"""Documentation search tool with See Also traversal."""

import json
from functools import lru_cache
from typing import Annotated, cast

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.docs import build_related_tree, normalize_doc_request
from tenzir_mcp.server import mcp
from tenzir_mcp.tools.documentation.backends.sqlite import SQLiteSearchBackend

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_search_backend() -> SQLiteSearchBackend:
    """Lazily instantiate the search backend to avoid import-time failures."""
    return SQLiteSearchBackend()


@mcp.tool(
    name="docs_search",
    tags={"documentation"},
    annotations={
        "title": "Search documentation",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def docs_search(
    query: Annotated[
        str | None,
        Field(
            default=None,
            description="Search keyword or phrase to find in documentation titles, names, categories, and examples",
        ),
    ] = None,
    search_type: Annotated[
        str,
        Field(
            default="all",
            description=(
                "Filter results by category: 'all', 'tutorials', 'guides', 'explanations', "
                "'integrations', or 'reference' (includes operators, functions, API, etc.)"
            ),
        ),
    ] = "all",
    limit: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=100,
            description="Maximum number of search results to return",
        ),
    ] = 10,
    depth: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            le=3,
            description="How many levels of 'See Also' relationships to expand (0 = no expansion)",
        ),
    ] = 0,
    paths: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Specific documentation paths to retrieve and expand (e.g., ['reference/operators/from'])",
        ),
    ] = None,
) -> ToolResult:
    """Search documentation by keyword or retrieve specific paths with 'See Also' expansion.

    Use this tool to:
    - Find operators or functions by keyword or query phrase
    - Discover related documentation through 'See Also' links (`depth` > 0)
    - Explore specific documentation areas (`search_type` filter)
    - Learn about unfamiliar concepts or workflows

    The depth parameter traverses cross-references, helping you discover
    operators and functions you might not have known about.
    """
    if depth < 0:
        error_msg = "Depth must not be negative."
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
    if limit <= 0:
        error_msg = "Limit must be greater than zero."
        return ToolResult(content=error_msg, structured_content={"error": error_msg})

    normalized_type = search_type.lower()
    valid_types = {
        "all",
        "tutorials",
        "guides",
        "explanations",
        "integrations",
        "reference",
    }
    if normalized_type not in valid_types:
        error_msg = f"Unsupported search_type '{search_type}'. Valid types: {', '.join(sorted(valid_types))}"
        return ToolResult(content=error_msg, structured_content={"error": error_msg})

    has_query = bool(query and query.strip())
    has_paths = bool(paths)
    if not has_query and not has_paths:
        error_msg = "Provide a non-empty query or at least one path."
        return ToolResult(content=error_msg, structured_content={"error": error_msg})

    try:
        backend = _get_search_backend()
    except FileNotFoundError as err:
        error_msg = (
            "Documentation search is unavailable because the docs database is missing. "
            "Run 'make update-docs && make build-doc-index && make build-doc-db' to generate it."
        )
        logger.warning("docs_search unavailable: %s", err)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})

    try:
        index = backend.get_all_docs()
        results: list[dict] = []

        if has_paths:
            unique_paths = []
            seen = set()
            for path in paths or []:
                normalized = normalize_doc_request(path)
                if normalized not in seen:
                    unique_paths.append(normalized)
                    seen.add(normalized)

            for path in unique_paths[:limit]:
                node = build_related_tree(path, index, depth, {path})
                if node:
                    results.append(node)

        if has_query:
            query_value = query.strip() if query else ""
            seen_paths: set[str | None] = {item.get("path") for item in results}

            # Determine which doc types to search
            doc_types_filter: list[str] | None = None
            if normalized_type != "all":
                type_mapping = {
                    "tutorials": ["tutorial"],
                    "guides": ["guide"],
                    "explanations": ["explanation"],
                    "integrations": ["integration"],
                    "reference": [
                        "operator",
                        "function",
                        "api",
                        "mcp",
                        "test",
                        "changelog",
                        "reference",
                    ],
                }
                doc_types_filter = type_mapping.get(normalized_type, [normalized_type])

            # Use backend to search
            search_results = backend.search(
                query_value,
                doc_types=doc_types_filter,
                limit=max(0, limit - len(results)),
            )

            # Filter out already-seen paths and add depth traversal
            for candidate in search_results:
                path_value = candidate.get("path")
                if not path_value or path_value in seen_paths:
                    continue
                seen_paths.add(path_value)

                # Add depth traversal if requested
                if depth > 0:
                    normalized_path = normalize_doc_request(path_value)
                    related_tree = build_related_tree(
                        normalized_path,
                        index,
                        depth,
                        {normalized_path},
                    )
                    if related_tree:
                        candidate["see_also"] = related_tree.get("see_also", [])
                        if related_tree.get("related"):
                            candidate["related"] = related_tree["related"]

                # Ensure see_also exists
                candidate.setdefault("see_also", [])
                results.append(candidate)

        response = {
            "results": results[:limit],
            "count": len(results[:limit]),
        }
        if has_query:
            response["query"] = query.strip() if query else ""
        if has_paths:
            response["paths"] = unique_paths[:limit]

        # Create human-readable summary
        summary_parts = []
        count_value = cast(int, response["count"])
        if count_value > 0:
            summary_parts.append(f"Found {count_value} result(s)")
            if has_query:
                query_str = cast(str, response["query"])
                summary_parts.append(f"for query '{query_str}'")
            if depth > 0:
                summary_parts.append(f"with {depth} level(s) of related docs")
        else:
            summary_parts.append("No results found")
            if has_query:
                summary_parts.append(f"for query '{query.strip() if query else ''}'")

        response_json = json.dumps(response, indent=2, sort_keys=True)
        content = f"{' '.join(summary_parts)}\n\n```json\n{response_json}\n```"

        return ToolResult(
            content=content,
            structured_content=response,
        )
    except Exception as exc:
        logger.error("Failed to search documentation: %s", exc)
        error_msg = f"Failed to search documentation: {exc}"
        return ToolResult(content=error_msg, structured_content={"error": str(exc)})
