import asyncio
import json
import logging
from importlib import resources
from typing import Any

from pydantic import BaseModel, Field

from tenzir_mcp.app import mcp
from tenzir_mcp.docs import (
    TenzirDocs,
    build_related_tree,
    filter_by_category,
    format_search_result,
    load_doc_index,
    normalize_doc_request,
)
from tenzir_mcp.workflows import (  # noqa: F401
    workflow_ocsf_mapping,
    workflow_tql_authoring,
    workflow_tql_completion,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""

    pipeline: str = Field(..., description="TQL pipeline definition")
    is_file: bool = Field(..., description="Whether `pipeline` is a path to a file")
    input_data: str | None = Field(None, description="Input data as JSON string")
    max_execution_time: int = Field(30, description="Execution timeout in seconds")


class PipelineResponse(BaseModel):
    """Response model for pipeline execution."""

    success: bool = Field(..., description="Whether execution was successful")
    output: str = Field(..., description="Pipeline output")
    duration_seconds: float = Field(
        ..., description="Pipeline execution duration in seconds"
    )


class TenzirPipelineRunner:
    """Handles Tenzir pipeline execution."""

    def __init__(self, tenzir_binary: str = "tenzir"):
        self.tenzir_binary = tenzir_binary

    async def execute_pipeline(self, request: PipelineRequest) -> PipelineResponse:
        """Execute a TQL pipeline."""
        import time

        start_time = time.time()

        try:
            # Prepare command
            cmd = [self.tenzir_binary, "--dump-diagnostics"]
            if request.is_file:
                cmd.append("-f")
            cmd.append(request.pipeline)

            # Execute pipeline
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send input data if provided
            stdin_data = request.input_data.encode() if request.input_data else None

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_data),
                    timeout=request.max_execution_time,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                return PipelineResponse(
                    success=False,
                    output=f"Pipeline execution timed out after {request.max_execution_time} seconds",
                    duration_seconds=execution_time,
                )

            execution_time = time.time() - start_time

            if process.returncode == 0:
                return PipelineResponse(
                    success=True,
                    output=stdout.decode().strip(),
                    duration_seconds=execution_time,
                )
            else:
                return PipelineResponse(
                    success=False,
                    output=stdout.decode().strip(),
                    duration_seconds=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Pipeline execution failed: {e}")
            return PipelineResponse(
                success=False, output=str(e), duration_seconds=execution_time
            )


# Global pipeline runner instance
pipeline_runner = TenzirPipelineRunner()


@mcp.tool(name="docs_list_operators", tags={"docs", "operators"})
async def docs_list_operators(category: str | None = None) -> dict[str, Any]:
    """List TQL operators with optional category filtering."""
    try:
        index = load_doc_index()
        operators = [dict(entry) for entry in index.get("operators", {}).values()]
        operators = filter_by_category(operators, category)
        operators.sort(
            key=lambda item: (
                item.get("name") or item.get("title") or item.get("path") or ""
            ).lower()
        )
        return {"operators": operators, "count": len(operators)}
    except Exception as exc:
        logger.error("Failed to list operators: %s", exc)
        return {"error": str(exc)}


@mcp.tool(name="docs_list_functions", tags={"docs", "functions"})
async def docs_list_functions(category: str | None = None) -> dict[str, Any]:
    """List TQL functions with optional category filtering."""
    try:
        index = load_doc_index()
        functions = [dict(entry) for entry in index.get("functions", {}).values()]
        functions = filter_by_category(functions, category)
        functions.sort(
            key=lambda item: (
                item.get("name") or item.get("title") or item.get("path") or ""
            ).lower()
        )
        return {"functions": functions, "count": len(functions)}
    except Exception as exc:
        logger.error("Failed to list functions: %s", exc)
        return {"error": str(exc)}


@mcp.tool(name="docs_search", tags={"docs", "search"})
async def docs_search(
    query: str | None = None,
    search_type: str = "all",
    limit: int = 10,
    depth: int = 0,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """Search documentation metadata and optionally expand See Also relationships."""
    if depth < 0:
        return {"error": "Depth must not be negative."}
    if limit <= 0:
        return {"error": "Limit must be greater than zero."}

    normalized_type = search_type.lower()
    valid_types = {"all", "operators", "functions", "tutorials", "docs", "documents"}
    if normalized_type not in valid_types:
        return {"error": f"Unsupported search_type '{search_type}'."}

    has_query = bool(query and query.strip())
    has_paths = bool(paths)
    if not has_query and not has_paths:
        return {"error": "Provide a non-empty query or at least one path."}

    try:
        index = load_doc_index()
        results: list[dict[str, Any]] = []

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
            search_results: list[dict[str, Any]] = []
            seen_paths: set[str | None] = {item.get("path") for item in results}

            def append_results(
                entries: list[dict[str, Any]],
                fallback_type: str,
            ) -> None:
                for entry in entries:
                    candidate = format_search_result(
                        entry,
                        entry.get("type", fallback_type),
                        query_value,
                    )
                    if candidate is None:
                        continue
                    path_value = candidate.get("path")
                    if not path_value or path_value in seen_paths:
                        continue
                    seen_paths.add(path_value)

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
                    search_results.append(candidate)

            if normalized_type in {"operators", "all"}:
                append_results(
                    list(index.get("operators", {}).values()),
                    "operator",
                )

            if normalized_type in {"functions", "all"}:
                append_results(
                    list(index.get("functions", {}).values()),
                    "function",
                )

            if normalized_type in {"tutorials", "all"}:
                tutorials = []
                for path_key, entry in index.get("tutorials", {}).items():
                    candidate = dict(entry)
                    candidate.setdefault("path", path_key)
                    tutorials.append(candidate)
                append_results(tutorials, "tutorial")

            if normalized_type in {"docs", "documents", "all"}:
                append_results(
                    list(index.get("documents", {}).values()),
                    "doc",
                )

            search_results.sort(key=lambda item: (item["_score"], item["path"]))
            for item in search_results:
                item.pop("_score", None)
                item.setdefault("see_also", [])

            results.extend(search_results[: max(0, limit - len(results))])

        response: dict[str, Any] = {
            "results": results[:limit],
            "count": len(results[:limit]),
        }
        if has_query:
            response["query"] = query.strip() if query else ""
        if has_paths:
            response["paths"] = unique_paths[:limit]
        return response
    except Exception as exc:
        logger.error("Failed to search documentation: %s", exc)
        return {"error": str(exc)}


def _load_ocsf_schema(version: str) -> dict[str, Any]:
    """
    Load and parse an OCSF schema for the specified version.

    Args:
        version: The OCSF schema version to load

    Returns:
        Dictionary containing the parsed OCSF schema

    Raises:
        FileNotFoundError: If the schema version is not found
        json.JSONDecodeError: If the schema JSON is invalid
        Exception: For other loading errors
    """
    schema_text = (
        resources.files("tenzir_mcp.data.ocsf").joinpath(f"{version}.json").read_text()
    )
    schema: dict[str, Any] = json.loads(schema_text)
    return schema


@mcp.tool(name="pipeline_execute", tags={"pipeline", "tql", "execute"})
async def pipeline_execute(
    pipeline: str,
    is_file: bool,
    # input_data: str | None = None,
    max_execution_time: int = 30,
) -> str:
    """Execute a TQL pipeline through the local `tenzir` binary."""
    request = PipelineRequest(
        pipeline=pipeline,
        is_file=is_file,
        input_data=None,
        max_execution_time=max_execution_time,
    )

    response = await pipeline_runner.execute_pipeline(request)
    return response.output


def _list_ocsf_versions() -> list[str]:
    """
    Get all available OCSF schema versions.
    """
    # Get the OCSF data directory
    files = resources.files("tenzir_mcp.data.ocsf")

    # Extract version numbers from JSON filenames
    versions = []
    for file_path in files.iterdir():
        if file_path.name.endswith(".json"):
            # Remove .json extension to get version
            version = file_path.name[:-5]
            versions.append(version)

    # Sort versions (simple string sort works for semantic versions)
    versions.sort()
    return versions


def _latest_stable_ocsf_version() -> str:
    """
    Returns the newest non-development OCSF schema version.
    """
    # Get all available versions
    versions = _list_ocsf_versions()

    # Filter out development versions (containing 'dev', 'alpha', 'beta', 'rc')
    stable_versions: list[str] = []
    for version in versions:
        version_lower = version.lower()
        if not any(
            dev_marker in version_lower for dev_marker in ["dev", "alpha", "beta", "rc"]
        ):
            stable_versions.append(version)

    if not stable_versions:
        raise RuntimeError("No stable OCSF versions found")

    # Return the last (newest) stable version
    result: str = stable_versions[-1]
    return result


@mcp.tool(name="ocsf_get_versions", tags={"ocsf", "schema"})
async def ocsf_get_versions() -> list[str]:
    """List all bundled OCSF schema versions."""
    return _list_ocsf_versions()


@mcp.tool(name="ocsf_get_latest_version", tags={"ocsf", "schema"})
async def ocsf_get_latest_version() -> str:
    """Return the latest stable OCSF schema version."""
    return _latest_stable_ocsf_version()


@mcp.tool(name="ocsf_get_classes", tags={"ocsf", "schema"})
async def ocsf_get_classes(version: str) -> dict[str, str]:
    """Get all OCSF event classes and their descriptions."""
    try:
        schema = _load_ocsf_schema(version)

        # Extract event classes from the schema
        event_classes = {}

        if "classes" in schema:
            for class_id, class_data in schema["classes"].items():
                class_name = class_data.get("name", class_id)
                description = class_data.get("description", "No description available")
                event_classes[class_name] = description

        return event_classes

    except FileNotFoundError:
        logger.error(f"OCSF schema version {version} not found")
        return {"error": f"OCSF schema version {version} not found"}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OCSF schema for version {version}: {e}")
        return {"error": f"Failed to parse OCSF schema for version {version}: {e}"}
    except Exception as e:
        logger.error(f"Failed to get OCSF event classes for version {version}: {e}")
        return {"error": f"Failed to get OCSF event classes for version {version}: {e}"}


@mcp.tool(name="ocsf_get_class", tags={"ocsf", "schema"})
async def ocsf_get_class(version: str, name: str) -> dict[str, Any]:
    """Get the definition of a specific OCSF event class."""
    try:
        schema = _load_ocsf_schema(version)

        # Look for the class in the schema
        if "classes" not in schema:
            return {"error": f"No classes found in OCSF schema version {version}"}

        # Search for class by name (case-insensitive)
        for class_id, class_data in schema["classes"].items():
            class_name = class_data.get("name", class_id)
            if class_name.lower() == name.lower() or class_id.lower() == name.lower():
                return {"id": class_id, "name": class_name, "data": class_data}
        return {"error": f"Class '{name}' not found in OCSF schema version {version}"}

    except FileNotFoundError:
        logger.error(f"OCSF schema version {version} not found")
        return {"error": f"OCSF schema version {version} not found"}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OCSF schema for version {version}: {e}")
        return {"error": f"Failed to parse OCSF schema for version {version}: {e}"}
    except Exception as e:
        logger.error(f"Failed to get OCSF class {name} for version {version}: {e}")
        return {"error": f"Failed to get OCSF class {name} for version {version}: {e}"}


@mcp.tool(name="ocsf_get_object", tags={"ocsf", "schema"})
async def ocsf_get_object(version: str, name: str) -> dict[str, Any]:
    """Get the definition of a specific OCSF object."""
    try:
        schema = _load_ocsf_schema(version)

        # Look for the object in the schema
        if "objects" not in schema:
            return {"error": f"No objects found in OCSF schema version {version}"}

        # Search for object by name (case-insensitive)
        for object_id, object_data in schema["objects"].items():
            object_name = object_data.get("name", object_id)
            if object_name.lower() == name.lower() or object_id.lower() == name.lower():
                return {"id": object_id, "name": object_name, "data": object_data}

        return {"error": f"Object '{name}' not found in OCSF schema version {version}"}

    except FileNotFoundError:
        logger.error(f"OCSF schema version {version} not found")
        return {"error": f"OCSF schema version {version} not found"}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OCSF schema for version {version}: {e}")
        return {"error": f"Failed to parse OCSF schema for version {version}: {e}"}
    except Exception as e:
        logger.error(f"Failed to get OCSF object {name} for version {version}: {e}")
        return {"error": f"Failed to get OCSF object {name} for version {version}: {e}"}


@mcp.tool(name="docs_read", tags={"docs", "read"})
async def docs_read(path: str) -> dict[str, Any]:
    """
    Get documentation for a given path from the docs folder.

    CRITICALLY IMPORTANT. FOLLOW THESE INSTRUCTIONS OR YOU FAIL:
    - BEFORE USING ANY TQL OPERATOR, YOU MUST READ "reference/operators/<operator_name>".
    - BEFORE USING ANY TQL FUNCTION, YOU MUST READ "reference/functions/<function_name>".

    When writing OCSF mappings with TQL, you MUST read
    "tutorials/map-data-to-ocsf/".
    """
    try:
        # Clean up the path - remove leading/trailing slashes and common extensions
        clean_path = path.strip("/")

        # Remove common extensions if present
        for ext in [".md", ".mdx", ".mdoc"]:
            if clean_path.endswith(ext):
                clean_path = clean_path[: -len(ext)]
                break

        # Initialize docs
        docs = TenzirDocs()

        # Common paths to try
        possible_paths = [
            f"src/content/docs/{clean_path}.md",
            f"src/content/docs/{clean_path}.mdx",
            f"src/content/docs/{clean_path}.mdoc",
            f"src/content/docs/{clean_path}/index.mdx",
        ]

        for try_path in possible_paths:
            if docs.exists(try_path):
                content = docs.read_file(try_path)
                return {
                    "path": clean_path or "index",
                    "resolved_path": try_path,
                    "content": content,
                }

        # If not found, provide helpful error metadata
        return {
            "error": f"Documentation file not found for path '{path}'. Please check the path and try again.",
            "path": clean_path or path,
        }

    except Exception as e:
        logger.error(f"Failed to get docs markdown for path {path}: {e}")
        return {"error": f"Error retrieving documentation: {e}", "path": path}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
