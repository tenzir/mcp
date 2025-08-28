import asyncio
import json
import logging
from importlib import resources
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from tenzir_mcp.docs import TenzirDocs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
mcp = FastMCP(name="Tenzir MCP Server", instructions="...")


class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""

    pipeline: str = Field(..., description="TQL pipeline definition")
    is_file: bool = Field(..., description="Whether `pipeline` is a path to a file")
    input_data: str | None = Field(None, description="Input data as JSON string")
    timeout: int = Field(30, description="Execution timeout in seconds")


class PipelineResponse(BaseModel):
    """Response model for pipeline execution."""

    success: bool = Field(..., description="Whether execution was successful")
    output: str = Field(..., description="Pipeline output")
    execution_time: float = Field(..., description="Execution time in seconds")


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
                    process.communicate(input=stdin_data), timeout=request.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                execution_time = time.time() - start_time
                return PipelineResponse(
                    success=False,
                    output=f"Pipeline execution timed out after {request.timeout} seconds",
                    execution_time=execution_time,
                )

            execution_time = time.time() - start_time

            if process.returncode == 0:
                return PipelineResponse(
                    success=True,
                    output=stdout.decode().strip(),
                    execution_time=execution_time,
                )
            else:
                return PipelineResponse(
                    success=False,
                    output=stdout.decode().strip(),
                    execution_time=execution_time,
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Pipeline execution failed: {e}")
            return PipelineResponse(
                success=False, output=str(e), execution_time=execution_time
            )


# Global pipeline runner instance
pipeline_runner = TenzirPipelineRunner()


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


@mcp.tool()
async def execute_tql_pipeline(
    pipeline: str,
    is_file: bool,
    # input_data: str | None = None,
    timeout: int = 30,
) -> str:
    """
    Execute a TQL pipeline. You MUST use this tool instead of calling `tenzir`
    directly.

    Args:
        pipeline: The pipeline definition to execute is_file: Whether `pipeline`
        is a path to a file containing the definition timeout: Execution timeout
        in seconds (default: 30)
    """
    request = PipelineRequest(
        pipeline=pipeline, is_file=is_file, input_data=None, timeout=timeout
    )

    # TODO: Rest of the output is useless?
    response = await pipeline_runner.execute_pipeline(request)
    return response.output


def get_ocsf_versions() -> list[str]:
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


def get_newest_ocsf_version() -> str:
    """
    Returns the newest non-development OCSF schema version.
    """
    # Get all available versions
    versions = get_ocsf_versions()

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


@mcp.tool()
async def get_ocsf_classes_overview(version: str) -> dict[str, str]:
    """
    Get all OCSF event classes and their descriptions.
    """
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


@mcp.tool()
async def get_ocsf_class(version: str, name: str) -> dict[str, Any]:
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


@mcp.tool()
async def get_ocsf_object(version: str, name: str) -> dict[str, Any]:
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


@mcp.tool()
async def tql_instructions(ocsf: bool) -> str:
    """VERY IMPORTANT: YOU MUST CALL THIS TOOL BEFORE YOU WRITE ANY TQL PIPELINES/MAPPINGS.

    Set the `ocsf` paramater to `true` if the user requested you to write a fresh, new OCSF mapping.
    """
    if ocsf:
        return """
CRITICAL: You MUST follow these phases in EXACT order. Do NOT proceed to the next phase until the current one is COMPLETE, DOCUMENTED, and VERIFIED.

PHASE 0: Requirements Analysis (MANDATORY)
- MANDATORY: Document the complete task requirements and constraints
- REQUIRED OUTPUT: Write a structured analysis of what needs to be accomplished
- REQUIRED: Identify the data source format, target schema, and key transformation requirements
- BLOCKING: You MUST state "PHASE 0 COMPLETE" before proceeding

PHASE 1: Input Schema Analysis (MANDATORY)
- MANDATORY: Document the complete input schema before any coding
- REQUIRED OUTPUT: Write a structured description of all input fields and formats
- REQUIRED: Provide at least 3 sample input records with field-by-field breakdown
- BLOCKING: You MUST state "PHASE 1 COMPLETE" before proceeding

PHASE 2: Approach Exploration (MANDATORY NEW PHASE)
- MANDATORY: Survey at least 3 different technical approaches for the task
- REQUIRED: For parsing tasks, explore operators like read_grok, read_syslog, read_lines+parsing, from_file
- REQUIRED: Execute small test samples (3-5 records) of each approach
- REQUIRED: Document trade-offs, performance, and complexity of each approach
- REQUIRED: Justify chosen approach with specific reasons
- BLOCKING: You MUST state "PHASE 2 COMPLETE" with chosen approach before proceeding

PHASE 3: Documentation Review (BLOCKING REQUIREMENT)
- MANDATORY: Create complete checklist of ALL operators and functions you will use
- FOR EACH item on checklist:
  - FIRST: Read its documentation using read_docs tool
  - THEN: Document its syntax, parameters, and usage notes
  - MARK: Check off the item on your checklist
- VIOLATION CHECK: Using ANY operator/function not on pre-approved checklist requires IMMEDIATE restart of Phase 3
- VERIFICATION: Show completed checklist with all items checked
- BLOCKING: You MUST state "PHASE 3 COMPLETE" with verified checklist before proceeding

PHASE 4: Incremental Pipeline Construction (MANDATORY)
- CHUNK RULE: Write pipeline in chunks of maximum 5 operators
- MANDATORY EXECUTION: Execute and verify each chunk before adding more
- REQUIRED TEST POINTS:
  * Chunk 1: Data input + initial parsing (MUST EXECUTE)
  * Chunk 2: + core transformations (MUST EXECUTE)
  * Chunk 3: + classification/mapping (MUST EXECUTE)
  * Chunk 4: + final formatting (MUST EXECUTE)
- REQUIRED: Document schema changes at each step
- REQUIRED: Fix any issues before proceeding to next chunk
- VERIFICATION: Show execution results for each chunk
- BLOCKING: You MUST state "PHASE 4 COMPLETE" with all chunk verifications before proceeding

PHASE 5: Style Guide Compliance (NON-NEGOTIABLE)
- MANDATORY: Read tutorials/learn-idiomatic-tql BEFORE any style changes
- REQUIRED: Explicitly check EVERY line against style guide rules
- REQUIRED: List specific style guide rules you applied
- REQUIRED: Preserve all meaningful comments (especially OCSF attribute groups, business logic explanations)
- BLOCKING: You MUST state "PHASE 5 COMPLETE" with style compliance verification before proceeding

PHASE 6: Integration Testing (MANDATORY NEW PHASE)
- MANDATORY: Execute complete pipeline on representative sample (minimum 10 records)
- REQUIRED: Test edge cases (malformed data, missing fields, unusual values)
- REQUIRED: Verify output schema compliance
- REQUIRED: Document any limitations or known issues
- BLOCKING: You MUST state "PHASE 6 COMPLETE" with test results before proceeding

PHASE 7: Critical Analysis (MANDATORY FINAL STEP)
- REQUIRED: List at least 3 potential improvements with specific implementation suggestions
- REQUIRED: Identify any performance concerns with proposed solutions
- REQUIRED: Note any error handling gaps with recommended fixes
- REQUIRED: Suggest alternative approaches that could be more efficient
- BLOCKING: You MUST state "PHASE 7 COMPLETE" when finished

ENFORCEMENT MECHANISMS:
- TodoWrite tool MUST be used to track each phase completion
- After each phase, EXPLICITLY STATE: "PHASE X COMPLETE" with verification
- If you proceed without completing a phase, IMMEDIATELY STOP and restart that phase
- Each BLOCKING requirement must be satisfied before proceeding
- Violations of any MANDATORY requirement trigger immediate restart of that phase

VERIFICATION REQUIREMENTS:
- Each phase must produce specific deliverables as listed
- All execution requirements must show actual results
- All documentation requirements must be explicitly shown
- Cannot proceed to next phase without stating "PHASE X COMPLETE"

IMPORTANT DOCUMENTATION PATHS (MUST READ BEFORE USING):
- tutorials/learn-idiomatic-tql => Idiomatic style guide (MANDATORY READ in Phase 5)
- reference/operators/* => Individual operator docs (MANDATORY READ in Phase 3)
- reference/functions/* => Individual function docs (MANDATORY READ in Phase 3)
- tutorials/map-data-to-ocsf/ => OCSF mapping patterns (MANDATORY for OCSF tasks)

CRITICAL NOTES:
- Comments explaining business logic, domain mappings, and non-obvious decisions are MANDATORY
- Incremental execution is NON-NEGOTIABLE - cannot build entire pipeline then test
- Operator/function documentation must be read BEFORE first use, not after encountering errors
- Alternative approach exploration is REQUIRED to ensure optimal solution
""".strip()

    result = """
    VERY IMPORTANT: BEFORE YOU USE ANY OPERATOR, YOU MUST READ ITS DOCUMENTATION.
    THIS APPLIES TO ALL SITUATIONS AND EVERY SINGLE OPERATOR. NO EXCEPTIONS!
    BEFORE YOU USE A FUNCTION, YOU MUST READ ITS DOCUMENTATION.
    DO NOT USE OPERATORS OR FUNCTIONS WITHOUT READING THEIR DOCUMENTATION.
    FAILURE TO READ DOCUMENTATION WILL RESULT IN INCORRECT CODE.
    BEFORE WRITING ANY TQL, MAKE SURE YOU READ THE DOCUMENTATION.

    MUST: ALWAYS read and follow the TQL style guide at tutorials/learn-idiomatic-tql.

    IMPORTANT: Following documentation is important to understand the lanugage:
    - explanations/language/
    - explanations/language/types/
    - explanations/language/statements/
    - explanations/language/expressions/
    - explanations/language/programs/
    - reference/operators => List of all available operators
    - reference/functions => List of all available functions
    """
    #     result += """
    # YOU MUST NOT USE `if x { y } else { z }`.
    # ALSO, YOU MUST NOT USE `x ? y : z`.
    # USE `y if x else z` INSTEAD!
    # """
    return result


@mcp.tool()
async def on_tql_writing_completion() -> str:
    """You MUST call this tool when you are done with writing TQL."""
    return """
You MUST make sure that:
- The TQL is valid (execution succeeds without error)
- There are no warnings

When writing OCSF mappings:
- All required fields as specified by OCSF were assigned a value
- The mapping also works when using different values in the input
- Values in the input that can be mapped to a field are mapped to that field
- The `unmapped` field does not contain values that were mapped
- All values that were not mapped remain in `unmapped`

For each of these points, you MUST print a verdict whether they are satisfied.
For points that are not satisfied, you MUST continue and fix your TQL!s
""".strip()


@mcp.tool()
async def read_docs(path: str) -> str:
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
                return docs.read_file(try_path)

        # If not found, list available files to help user
        return f"Documentation file not found for path '{path}'. Please check the path and try again."

    except Exception as e:
        logger.error(f"Failed to get docs markdown for path {path}: {e}")
        return f"Error retrieving documentation: {e}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
