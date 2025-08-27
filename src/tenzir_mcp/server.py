import asyncio
import json
import logging
from importlib import resources
from typing import Any

from fastmcp import FastMCP, Context
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
    Execute a TQL (Tenzir Query Language) pipeline.

    Whenever you are writing TQL, you MUST either validate or execute it. If there
    are no side-effects, execute instead of validate.

    You MUST try to fix all warnings and errors!

    Args:
        pipeline: The pipeline definition to execute
        is_file: Whether `pipeline` is a path to a file containing the definition
        input_data: Optional input data as JSON string
        timeout: Execution timeout in seconds (default: 30)

    Returns:
        Dictionary containing execution results
    """
    request = PipelineRequest(
        pipeline=pipeline, is_file=is_file, input_data=None, timeout=timeout
    )

    # TODO: Rest of the output is useless?
    response = await pipeline_runner.execute_pipeline(request)
    return response.output


# @mcp.tool()
async def validate_tql_pipeline(pipeline: str) -> str:
    """
    Validate a TQL pipeline syntax without executing it. You can also use this
    when there is no destination yet. This allows you to check the syntax before
    finishing the pipeline.
    """
    try:
        # Use tenzir with --dry-run flag to validate syntax
        cmd = ["tenzir", "--dump-pipeline", "--dump-diagnostics", pipeline]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            return "Pipeline syntax is valid"
        else:
            return stdout.decode()
    except Exception as e:
        logger.error(f"Pipeline validation failed: {e}")
        return f"Exception: {e}"


# @mcp.tool()
async def get_ocsf_versions() -> list[str]:
    """
    Get all available OCSF schema versions.
    """
    try:
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

    except Exception as e:
        logger.error(f"Failed to get OCSF versions: {e}")
        return [f"Error: Failed to get OCSF versions: {e}"]


# @mcp.tool()
async def default_ocsf_version() -> str:
    """
    Returns the newest non-development OCSF schema version.

    Call this when you need an OCSF version but the user did not specify one.
    """
    try:
        # Get all available versions
        versions = await get_ocsf_versions.fn()

        # Filter out development versions (containing 'dev', 'alpha', 'beta', 'rc')
        stable_versions: list[str] = []
        for version in versions:
            version_lower = version.lower()
            if not any(
                dev_marker in version_lower
                for dev_marker in ["dev", "alpha", "beta", "rc"]
            ):
                stable_versions.append(version)

        if not stable_versions:
            logger.warning("No stable OCSF versions found")
            return "Error: No stable OCSF versions found"

        # Return the last (newest) stable version
        result: str = stable_versions[-1]
        return result

    except Exception as e:
        logger.error(f"Failed to get default OCSF version: {e}")
        return f"Error: Failed to get default OCSF version: {e}"


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


# @mcp.tool()
async def ocsf_instructions_generic() -> str:
    """Provides generic instructions when writing OCSF mappings."""
    return """
- You MUST NOT use `|` to separate operators. Use newlines instead.
- TQL has `if` statements, and `if` expressions. To use `if` expressions,
  write `<expr> if <expr> else <expr>`. Ternary `?` does not exist.
- Do not hardcode OCSF fields to specific values just because that values
  are set that way in the input example. Treat everything derived from the
  input as having the possibility of changing.
- Make sure that if the value of a field is fully reflected in the resulting
  OCSF event, that the field is removed from the input object. Its value MUST
  NOT end up in `unmapped` at the end of the mapping! You MUST try to use `move`
  expressions instead of `drop` if possible. That is, instead of `x = y.z`
  followed by `drop y.z`, you MUST use `x = move y.z`. Note that `move` can only
  be applied to fields! You MUST NOT use `move` in the position of a statement,
  only inside an expression!
- You may drop unused fields if you are certain they stay the same between
  events. For example, an `event_kind` field with the type of the event.
- Whenever you are not absolutely sure that certain syntax or functions
  exist within TQL, you must consult the docs tools.
- When you are not absolutely sure about the OCSF schema, for example
  whether a field exists, consult the OCSF tools.
- Execute the mapping pipeline. You MUST fix all warnings. Before fixing a
  warning.
""".strip()


@mcp.tool()
async def tql_instructions(ctx: Context) -> str:
    """VERY IMPORTANT: You MUST call this tool BEFORE you write any TQL (once per session)."""
    result = ""
    # print(await ctx.sample("Test"))
    for path in [
        "explanations/language/",
        "explanations/language/types/",
        "explanations/language/statements/",
        "explanations/language/expressions/",
        "explanations/language/programs/",
        "tutorials/learn-idiomatic-tql",
    ]:
        result += await read_docs.fn(path)
    result += """
YOU MUST NOT USE `if x { y } else { z }`.
ALSO, YOU MUST NOT USE `x ? y : z`.
USE `y if x else z` INSTEAD!
"""
    return result
    result += """# Operators

Tenzir comes with a wide range of built-in pipeline operators.

## Analyze

[Section titled “Analyze”](#analyze)

### [rare](/reference/operators/rare)

[→](/reference/operators/rare)

Shows the least common values.

```tql
rare auth.token
```

### [reverse](/reference/operators/reverse)

[→](/reference/operators/reverse)

Reverses the event order.

```tql
reverse
```

### [sort](/reference/operators/sort)

[→](/reference/operators/sort)

Sorts events by the given expressions.

```tql
sort name, -abs(transaction)
```

### [summarize](/reference/operators/summarize)

[→](/reference/operators/summarize)

Groups events and applies aggregate functions to each group.

```tql
summarize name, sum(amount)
```

### [top](/reference/operators/top)

[→](/reference/operators/top)

Shows the most common values.

```tql
top user
```

## Charts

[Section titled “Charts”](#charts)

### [chart\_area](/reference/operators/chart_area)

[→](/reference/operators/chart_area)

Plots events on an area chart.

```tql
chart_area …
```

### [chart\_bar](/reference/operators/chart_bar)

[→](/reference/operators/chart_bar)

Plots events on an bar chart.

```tql
chart_bar …
```

### [chart\_line](/reference/operators/chart_line)

[→](/reference/operators/chart_line)

Plots events on an line chart.

```tql
chart_line …
```

### [chart\_pie](/reference/operators/chart_pie)

[→](/reference/operators/chart_pie)

Plots events on an pie chart.

```tql
chart_pie …
```

## Connecting Pipelines

[Section titled “Connecting Pipelines”](#connecting-pipelines)

### [publish](/reference/operators/publish)

[→](/reference/operators/publish)

Publishes events to a channel with a topic.

```tql
publish "topic"
```

### [subscribe](/reference/operators/subscribe)

[→](/reference/operators/subscribe)

Subscribes to events from a channel with a topic.

```tql
subscribe "topic"
```

## Contexts

[Section titled “Contexts”](#contexts)

### [context::create\_bloom\_filter](/reference/operators/context/create_bloom_filter)

[→](/reference/operators/context/create_bloom_filter)

Creates a Bloom filter context.

```tql
context::create_bloom_filter "ctx", capacity=1Mi, fp_probability=0.01
```

### [context::create\_geoip](/reference/operators/context/create_geoip)

[→](/reference/operators/context/create_geoip)

Creates a GeoIP context.

```tql
context::create_geoip "ctx", db_path="GeoLite2-City.mmdb"
```

### [context::create\_lookup\_table](/reference/operators/context/create_lookup_table)

[→](/reference/operators/context/create_lookup_table)

Creates a lookup table context.

```tql
context::create_lookup_table "ctx"
```

### [context::enrich](/reference/operators/context/enrich)

[→](/reference/operators/context/enrich)

Enriches events with data from a context.

```tql
context::enrich "ctx", key=x
```

### [context::erase](/reference/operators/context/erase)

[→](/reference/operators/context/erase)

Removes entries from a context.

```tql
context::erase "ctx", key=x
```

### [context::inspect](/reference/operators/context/inspect)

[→](/reference/operators/context/inspect)

Resets a context.

```tql
context::inspect "ctx"
```

### [context::list](/reference/operators/context/list)

[→](/reference/operators/context/list)

Lists all contexts

```tql
context::list
```

### [context::load](/reference/operators/context/load)

[→](/reference/operators/context/load)

Loads context state.

```tql
context::load "ctx"
```

### [context::remove](/reference/operators/context/remove)

[→](/reference/operators/context/remove)

Deletes a context.

```tql
context::remove "ctx"
```

### [context::reset](/reference/operators/context/reset)

[→](/reference/operators/context/reset)

Resets a context.

```tql
context::reset "ctx"
```

### [context::save](/reference/operators/context/save)

[→](/reference/operators/context/save)

Saves context state.

```tql
context::save "ctx"
```

### [context::update](/reference/operators/context/update)

[→](/reference/operators/context/update)

Updates a context with new data.

```tql
context::update "ctx", key=x, value=y
```

## Detection

[Section titled “Detection”](#detection)

### [sigma](/reference/operators/sigma)

[→](/reference/operators/sigma)

Filter the input with Sigma rules and output matching events.

```tql
sigma "/tmp/rules/"
```

### [yara](/reference/operators/yara)

[→](/reference/operators/yara)

Executes YARA rules on byte streams.

```tql
yara "/path/to/rules", blockwise=true
```

## Encode & Decode

[Section titled “Encode & Decode”](#encode--decode)

### [compress](/reference/operators/compress)

[→](/reference/operators/compress)

Compresses a stream of bytes.

```tql
compress "zstd"
```

### [compress\_brotli](/reference/operators/compress_brotli)

[→](/reference/operators/compress_brotli)

Compresses a stream of bytes using Brotli compression.

```tql
compress_brotli, level=10
```

### [compress\_bz2](/reference/operators/compress_bz2)

[→](/reference/operators/compress_bz2)

Compresses a stream of bytes using bz2 compression.

```tql
compress_bz2, level=9
```

### [compress\_gzip](/reference/operators/compress_gzip)

[→](/reference/operators/compress_gzip)

Compresses a stream of bytes using gzip compression.

```tql
compress_gzip, level=8
```

### [compress\_lz4](/reference/operators/compress_lz4)

[→](/reference/operators/compress_lz4)

Compresses a stream of bytes using lz4 compression.

```tql
compress_lz4, level=7
```

### [compress\_zstd](/reference/operators/compress_zstd)

[→](/reference/operators/compress_zstd)

Compresses a stream of bytes using zstd compression.

```tql
compress_zstd, level=6
```

### [decompress](/reference/operators/decompress)

[→](/reference/operators/decompress)

Decompresses a stream of bytes.

```tql
decompress "gzip"
```

### [decompress\_brotli](/reference/operators/decompress_brotli)

[→](/reference/operators/decompress_brotli)

Decompresses a stream of bytes in the Brotli format.

```tql
decompress_brotli
```

### [decompress\_bz2](/reference/operators/decompress_bz2)

[→](/reference/operators/decompress_bz2)

Decompresses a stream of bytes in the Bzip2 format.

```tql
decompress_bz2
```

### [decompress\_gzip](/reference/operators/decompress_gzip)

[→](/reference/operators/decompress_gzip)

Decompresses a stream of bytes in the Gzip format.

```tql
decompress_gzip
```

### [decompress\_lz4](/reference/operators/decompress_lz4)

[→](/reference/operators/decompress_lz4)

Decompresses a stream of bytes in the Lz4 format.

```tql
decompress_lz4
```

### [decompress\_zstd](/reference/operators/decompress_zstd)

[→](/reference/operators/decompress_zstd)

Decompresses a stream of bytes in the Zstd format.

```tql
decompress_zstd
```

## Escape Hatches

[Section titled “Escape Hatches”](#escape-hatches)

### [python](/reference/operators/python)

[→](/reference/operators/python)

Executes Python code against each event of the input.

```tql
python "self.x = self.y"
```

### [shell](/reference/operators/shell)

[→](/reference/operators/shell)

Executes a system command and hooks its stdin and stdout into the pipeline.

```tql
shell "echo hello"
```

## Filter

[Section titled “Filter”](#filter)

### [assert](/reference/operators/assert)

[→](/reference/operators/assert)

Drops events and emits a warning if the invariant is violated.

```tql
assert name.starts_with("John")
```

### [assert\_throughput](/reference/operators/assert_throughput)

[→](/reference/operators/assert_throughput)

Emits a warning if the pipeline does not have the expected throughput

```tql
assert_throughput 1000, within=1s
```

### [deduplicate](/reference/operators/deduplicate)

[→](/reference/operators/deduplicate)

Removes duplicate events based on a common key.

```tql
deduplicate src_ip
```

### [head](/reference/operators/head)

[→](/reference/operators/head)

Limits the input to the first `n` events.

```tql
head 20
```

### [sample](/reference/operators/sample)

[→](/reference/operators/sample)

Dynamically samples events from a event stream.

```tql
sample 30s, max_samples=2k
```

### [slice](/reference/operators/slice)

[→](/reference/operators/slice)

Keeps a range of events within the interval `[begin, end)` stepping by `stride`.

```tql
slice begin=10, end=30
```

### [tail](/reference/operators/tail)

[→](/reference/operators/tail)

Limits the input to the last `n` events.

```tql
tail 20
```

### [taste](/reference/operators/taste)

[→](/reference/operators/taste)

Limits the input to `n` events per unique schema.

```tql
taste 1
```

### [where](/reference/operators/where)

[→](/reference/operators/where)

Keeps only events for which the given predicate is true.

```tql
where name.starts_with("John")
```

## Flow Control

[Section titled “Flow Control”](#flow-control)

### [cron](/reference/operators/cron)

[→](/reference/operators/cron)

Runs a pipeline periodically according to a cron expression.

```tql
cron "* */10 * * * MON-FRI" { from "https://example.org" }
```

### [delay](/reference/operators/delay)

[→](/reference/operators/delay)

Delays events relative to a given start time, with an optional speedup.

```tql
delay ts, speed=2.5
```

### [discard](/reference/operators/discard)

[→](/reference/operators/discard)

Discards all incoming events.

```tql
discard
```

### [every](/reference/operators/every)

[→](/reference/operators/every)

Runs a pipeline periodically at a fixed interval.

```tql
every 10s { summarize sum(amount) }
```

### [fork](/reference/operators/fork)

[→](/reference/operators/fork)

Executes a subpipeline with a copy of the input.

```tql
fork { to "copy.json" }
```

### [load\_balance](/reference/operators/load_balance)

[→](/reference/operators/load_balance)

Routes the data to one of multiple subpipelines.

```tql
load_balance $over { publish $over }
```

### [pass](/reference/operators/pass)

[→](/reference/operators/pass)

Does nothing with the input.

```tql
pass
```

### [repeat](/reference/operators/repeat)

[→](/reference/operators/repeat)

Repeats the input a number of times.

```tql
repeat 100
```

### [throttle](/reference/operators/throttle)

[→](/reference/operators/throttle)

Limits the bandwidth of a pipeline.

```tql
throttle 100M, within=1min
```

## Host Inspection

[Section titled “Host Inspection”](#host-inspection)

### [files](/reference/operators/files)

[→](/reference/operators/files)

Shows file information for a given directory.

```tql
files "/var/log/", recurse=true
```

### [nics](/reference/operators/nics)

[→](/reference/operators/nics)

Shows a snapshot of available network interfaces.

```tql
nics
```

### [processes](/reference/operators/processes)

[→](/reference/operators/processes)

Shows a snapshot of running processes.

```tql
processes
```

### [sockets](/reference/operators/sockets)

[→](/reference/operators/sockets)

Shows a snapshot of open sockets.

```tql
sockets
```

## Internals

[Section titled “Internals”](#internals)

### [api](/reference/operators/api)

[→](/reference/operators/api)

Use Tenzir's REST API directly from a pipeline.

```tql
api "/pipeline/list"
```

### [batch](/reference/operators/batch)

[→](/reference/operators/batch)

The `batch` operator controls the batch size of events.

```tql
batch timeout=1s
```

### [buffer](/reference/operators/buffer)

[→](/reference/operators/buffer)

An in-memory buffer to improve handling of data spikes in upstream operators.

```tql
buffer 10M, policy="drop"
```

### [cache](/reference/operators/cache)

[→](/reference/operators/cache)

An in-memory cache shared between pipelines.

```tql
cache "w01wyhTZm3", ttl=10min
```

### [local](/reference/operators/local)

[→](/reference/operators/local)

Forces a pipeline to run locally.

```tql
local { sort foo }
```

### [measure](/reference/operators/measure)

[→](/reference/operators/measure)

Replaces the input with metrics describing the input.

```tql
measure
```

### [remote](/reference/operators/remote)

[→](/reference/operators/remote)

Forces a pipeline to run remotely at a node.

```tql
remote { version }
```

### [serve](/reference/operators/serve)

[→](/reference/operators/serve)

Make events available under the `/serve` REST API endpoint

```tql
serve "abcde12345"
```

### [strict](/reference/operators/strict)

[→](/reference/operators/strict)

Treats all warnings as errors.

```tql
strict { assert false }
```

### [unordered](/reference/operators/unordered)

[→](/reference/operators/unordered)

Removes ordering assumptions from a pipeline.

```tql
unordered { read_ndjson }
```

## Modify

[Section titled “Modify”](#modify)

### [dns\_lookup](/reference/operators/dns_lookup)

[→](/reference/operators/dns_lookup)

Performs DNS lookups to resolve IP addresses to hostnames or hostnames to IP addresses.

```tql
dns_lookup ip_address, result=dns_info
```

### [drop](/reference/operators/drop)

[→](/reference/operators/drop)

Removes fields from the event.

```tql
drop name, metadata.id
```

### [drop\_null\_fields](/reference/operators/drop_null_fields)

[→](/reference/operators/drop_null_fields)

Removes fields containing null values from the event.

```tql
drop_null_fields name, metadata.id
```

### [enumerate](/reference/operators/enumerate)

[→](/reference/operators/enumerate)

Add a field with the number of preceding events.

```tql
enumerate num
```

### [http](/reference/operators/http)

[→](/reference/operators/http)

Sends HTTP/1.1 requests and forwards the response.

```tql
http "example.com"
```

### [move](/reference/operators/move)

[→](/reference/operators/move)

Moves values from one field to another, removing the original field.

```tql
move id=parsed_id, ctx.message=incoming.status
```

### [replace](/reference/operators/replace)

[→](/reference/operators/replace)

Replaces all occurrences of a value with another value.

```tql
replace what=42, with=null
```

### [select](/reference/operators/select)

[→](/reference/operators/select)

Selects some values and discards the rest.

```tql
select name, id=metadata.id
```

### [set](/reference/operators/set)

[→](/reference/operators/set)

Assigns a value to a field, creating it if necessary.

```tql
name = "Tenzir"
```

### [timeshift](/reference/operators/timeshift)

[→](/reference/operators/timeshift)

Adjusts timestamps relative to a given start time, with an optional speedup.

```tql
timeshift ts, start=2020-01-01
```

### [unroll](/reference/operators/unroll)

[→](/reference/operators/unroll)

Returns a new event for each member of a list or a record in an event, duplicating the surrounding event.

```tql
unroll names
```

## OCSF

[Section titled “OCSF”](#ocsf)

### [ocsf::apply](/reference/operators/ocsf/apply)

[→](/reference/operators/ocsf/apply)

Casts incoming events to their OCSF type.

```tql
ocsf::apply
```

### [ocsf::derive](/reference/operators/ocsf/derive)

[→](/reference/operators/ocsf/derive)

Automatically assigns enum strings from their integer counterparts and vice versa.

```tql
ocsf::derive
```

### [ocsf::trim](/reference/operators/ocsf/trim)

[→](/reference/operators/ocsf/trim)

Drops fields from OCSF events to reduce their size.

```tql
ocsf::trim
```

## Packages

[Section titled “Packages”](#packages)

### [package::add](/reference/operators/package/add)

[→](/reference/operators/package/add)

Installs a package.

```tql
package::add "suricata-ocsf"
```

### [package::list](/reference/operators/package/list)

[→](/reference/operators/package/list)

Shows installed packages.

```tql
package::list
```

### [package::remove](/reference/operators/package/remove)

[→](/reference/operators/package/remove)

Uninstalls a package.

```tql
package::remove "suricata-ocsf"
```

### [pipeline::list](/reference/operators/pipeline/list)

[→](/reference/operators/pipeline/list)

Shows managed pipelines.

```tql
pipeline::list
```

## Parsing

[Section titled “Parsing”](#parsing)

### [read\_all](/reference/operators/read_all)

[→](/reference/operators/read_all)

Parses an incoming bytes stream into a single event.

```tql
read_all binary=true
```

### [read\_bitz](/reference/operators/read_bitz)

[→](/reference/operators/read_bitz)

Parses bytes as *BITZ* format.

```tql
read_bitz
```

### [read\_cef](/reference/operators/read_cef)

[→](/reference/operators/read_cef)

Parses an incoming Common Event Format (CEF) stream into events.

```tql
read_cef
```

### [read\_csv](/reference/operators/read_csv)

[→](/reference/operators/read_csv)

Read CSV (Comma-Separated Values) from a byte stream.

```tql
read_csv null_value="-"
```

### [read\_delimited](/reference/operators/read_delimited)

[→](/reference/operators/read_delimited)

Parses an incoming bytes stream into events using a string as delimiter.

```tql
read_delimited "|"
```

### [read\_delimited\_regex](/reference/operators/read_delimited_regex)

[→](/reference/operators/read_delimited_regex)

Parses an incoming bytes stream into events using a regular expression as delimiter.

```tql
read_delimited_regex r"\s+"
```

### [read\_feather](/reference/operators/read_feather)

[→](/reference/operators/read_feather)

Parses an incoming Feather byte stream into events.

```tql
read_feather
```

### [read\_gelf](/reference/operators/read_gelf)

[→](/reference/operators/read_gelf)

Parses an incoming GELF stream into events.

```tql
read_gelf
```

### [read\_grok](/reference/operators/read_grok)

[→](/reference/operators/read_grok)

Parses lines of input with a grok pattern.

```tql
read_grok "%{IP:client} %{WORD:action}"
```

### [read\_json](/reference/operators/read_json)

[→](/reference/operators/read_json)

Parses an incoming JSON stream into events.

```tql
read_json arrays_of_objects=true
```

### [read\_kv](/reference/operators/read_kv)

[→](/reference/operators/read_kv)

Read Key-Value pairs from a byte stream.

```tql
read_kv r"(\s+)[A-Z_]+:", r":\s*"
```

### [read\_leef](/reference/operators/read_leef)

[→](/reference/operators/read_leef)

Parses an incoming \[LEEF]\[leef] stream into events.

```tql
read_leef
```

### [read\_lines](/reference/operators/read_lines)

[→](/reference/operators/read_lines)

Parses an incoming bytes stream into events.

```tql
read_lines
```

### [read\_ndjson](/reference/operators/read_ndjson)

[→](/reference/operators/read_ndjson)

Parses an incoming NDJSON (newline-delimited JSON) stream into events.

```tql
read_ndjson
```

### [read\_parquet](/reference/operators/read_parquet)

[→](/reference/operators/read_parquet)

Reads events from a Parquet byte stream.

```tql
read_parquet
```

### [read\_pcap](/reference/operators/read_pcap)

[→](/reference/operators/read_pcap)

Reads raw network packets in PCAP file format.

```tql
read_pcap
```

### [read\_ssv](/reference/operators/read_ssv)

[→](/reference/operators/read_ssv)

Read SSV (Space-Separated Values) from a byte stream.

```tql
read_ssv header="name count"
```

### [read\_suricata](/reference/operators/read_suricata)

[→](/reference/operators/read_suricata)

Parse an incoming \[Suricata EVE JSON]\[eve-json] stream into events.

```tql
read_suricata
```

### [read\_syslog](/reference/operators/read_syslog)

[→](/reference/operators/read_syslog)

Parses an incoming Syslog stream into events.

```tql
read_syslog
```

### [read\_tsv](/reference/operators/read_tsv)

[→](/reference/operators/read_tsv)

Read TSV (Tab-Separated Values) from a byte stream.

```tql
read_tsv auto_expand=true
```

### [read\_xsv](/reference/operators/read_xsv)

[→](/reference/operators/read_xsv)

Read XSV from a byte stream.

```tql
read_xsv ";", ":", "N/A"
```

### [read\_yaml](/reference/operators/read_yaml)

[→](/reference/operators/read_yaml)

Parses an incoming YAML stream into events.

```tql
read_yaml
```

### [read\_zeek\_json](/reference/operators/read_zeek_json)

[→](/reference/operators/read_zeek_json)

Parse an incoming Zeek JSON stream into events.

```tql
read_zeek_json
```

### [read\_zeek\_tsv](/reference/operators/read_zeek_tsv)

[→](/reference/operators/read_zeek_tsv)

Parses an incoming `Zeek TSV` stream into events.

```tql
read_zeek_tsv
```

## Pipelines

[Section titled “Pipelines”](#pipelines)

### [pipeline::activity](/reference/operators/pipeline/activity)

[→](/reference/operators/pipeline/activity)

Summarizes the activity of pipelines.

```tql
pipeline::activity range=1d, interval=1h
```

### [pipeline::detach](/reference/operators/pipeline/detach)

[→](/reference/operators/pipeline/detach)

Starts a pipeline in the node.

```tql
pipeline::detach { … }
```

### [pipeline::list](/reference/operators/pipeline/list)

[→](/reference/operators/pipeline/list)

Shows managed pipelines.

```tql
pipeline::list
```

### [pipeline::run](/reference/operators/pipeline/run)

[→](/reference/operators/pipeline/run)

Starts a pipeline in the node and waits for it to complete.

```tql
pipeline::run { … }
```

## Printing

[Section titled “Printing”](#printing)

### [write\_bitz](/reference/operators/write_bitz)

[→](/reference/operators/write_bitz)

Writes events in *BITZ* format.

```tql
write_bitz
```

### [write\_csv](/reference/operators/write_csv)

[→](/reference/operators/write_csv)

Transforms event stream to CSV (Comma-Separated Values) byte stream.

```tql
write_csv
```

### [write\_feather](/reference/operators/write_feather)

[→](/reference/operators/write_feather)

Transforms the input event stream to Feather byte stream.

```tql
write_feather
```

### [write\_json](/reference/operators/write_json)

[→](/reference/operators/write_json)

Transforms the input event stream to a JSON byte stream.

```tql
write_json
```

### [write\_kv](/reference/operators/write_kv)

[→](/reference/operators/write_kv)

Writes events in a Key-Value format.

```tql
write_kv
```

### [write\_lines](/reference/operators/write_lines)

[→](/reference/operators/write_lines)

Writes events as key-value pairsthe *values* of an event.

```tql
write_lines
```

### [write\_ndjson](/reference/operators/write_ndjson)

[→](/reference/operators/write_ndjson)

Transforms the input event stream to a Newline-Delimited JSON byte stream.

```tql
write_ndjson
```

### [write\_parquet](/reference/operators/write_parquet)

[→](/reference/operators/write_parquet)

Transforms event stream to a Parquet byte stream.

```tql
write_parquet
```

### [write\_pcap](/reference/operators/write_pcap)

[→](/reference/operators/write_pcap)

Transforms event stream to PCAP byte stream.

```tql
write_pcap
```

### [write\_ssv](/reference/operators/write_ssv)

[→](/reference/operators/write_ssv)

Transforms event stream to SSV (Space-Separated Values) byte stream.

```tql
write_ssv
```

### [write\_syslog](/reference/operators/write_syslog)

[→](/reference/operators/write_syslog)

Writes events as syslog.

```tql
write_syslog
```

### [write\_tql](/reference/operators/write_tql)

[→](/reference/operators/write_tql)

Transforms the input event stream to a TQL notation byte stream.

```tql
write_tql
```

### [write\_tsv](/reference/operators/write_tsv)

[→](/reference/operators/write_tsv)

Transforms event stream to TSV (Tab-Separated Values) byte stream.

```tql
write_tsv
```

### [write\_xsv](/reference/operators/write_xsv)

[→](/reference/operators/write_xsv)

Transforms event stream to XSV byte stream.

```tql
write_xsv
```

### [write\_yaml](/reference/operators/write_yaml)

[→](/reference/operators/write_yaml)

Transforms the input event stream to YAML byte stream.

```tql
write_yaml
```

### [write\_zeek\_tsv](/reference/operators/write_zeek_tsv)

[→](/reference/operators/write_zeek_tsv)

Transforms event stream into Zeek Tab-Separated Value byte stream.

```tql
write_zeek_tsv
```

## Inputs

[Section titled “Inputs”](#inputs)

### Bytes

[Section titled “Bytes”](#bytes)

### [load\_amqp](/reference/operators/load_amqp)

[→](/reference/operators/load_amqp)

Loads a byte stream via AMQP messages.

```tql
load_amqp
```

### [load\_azure\_blob\_storage](/reference/operators/load_azure_blob_storage)

[→](/reference/operators/load_azure_blob_storage)

Loads bytes from Azure Blob Storage.

```tql
load_azure_blob_storage "abfs://container/file"
```

### [load\_file](/reference/operators/load_file)

[→](/reference/operators/load_file)

Loads the contents of the file at `path` as a byte stream.

```tql
load_file "/tmp/data.json"
```

### [load\_ftp](/reference/operators/load_ftp)

[→](/reference/operators/load_ftp)

Loads a byte stream via FTP.

```tql
load_ftp "ftp.example.org"
```

### [load\_gcs](/reference/operators/load_gcs)

[→](/reference/operators/load_gcs)

Loads bytes from a Google Cloud Storage object.

```tql
load_gcs "gs://bucket/object.json"
```

### [load\_google\_cloud\_pubsub](/reference/operators/load_google_cloud_pubsub)

[→](/reference/operators/load_google_cloud_pubsub)

Subscribes to a Google Cloud Pub/Sub subscription and obtains bytes.

```tql
load_google_cloud_pubsub project_id="my-project"
```

### [load\_http](/reference/operators/load_http)

[→](/reference/operators/load_http)

Loads a byte stream via HTTP.

```tql
load_http "example.org", params={n: 5}
```

### [load\_kafka](/reference/operators/load_kafka)

[→](/reference/operators/load_kafka)

Loads a byte stream from a Apache Kafka topic.

```tql
load_kafka topic="example"
```

### [load\_nic](/reference/operators/load_nic)

[→](/reference/operators/load_nic)

Loads bytes from a network interface card (NIC).

```tql
load_nic "eth0"
```

### [load\_s3](/reference/operators/load_s3)

[→](/reference/operators/load_s3)

Loads from an Amazon S3 object.

```tql
load_s3 "s3://my-bucket/obj.csv"
```

### [load\_sqs](/reference/operators/load_sqs)

[→](/reference/operators/load_sqs)

Loads bytes from \[Amazon SQS]\[sqs] queues.

```tql
load_sqs "sqs://tenzir"
```

### [load\_stdin](/reference/operators/load_stdin)

[→](/reference/operators/load_stdin)

Accepts bytes from standard input.

```tql
load_stdin
```

### [load\_tcp](/reference/operators/load_tcp)

[→](/reference/operators/load_tcp)

Loads bytes from a TCP or TLS connection.

```tql
load_tcp "0.0.0.0:8090" { read_json }
```

### [load\_udp](/reference/operators/load_udp)

[→](/reference/operators/load_udp)

Loads bytes from a UDP socket.

```tql
load_udp "0.0.0.0:8090"
```

### [load\_zmq](/reference/operators/load_zmq)

[→](/reference/operators/load_zmq)

Receives ZeroMQ messages.

```tql
load_zmq
```

### Events

[Section titled “Events”](#events)

### [from](/reference/operators/from)

[→](/reference/operators/from)

Obtains events from an URI, inferring the source, compression and format.

```tql
from "data.json"
```

### [from\_azure\_blob\_storage](/reference/operators/from_azure_blob_storage)

[→](/reference/operators/from_azure_blob_storage)

Reads one or multiple files from Azure Blob Storage.

```tql
from_azure_blob_storage "abfs://container/data/**.json"
```

### [from\_file](/reference/operators/from_file)

[→](/reference/operators/from_file)

Reads one or multiple files from a filesystem.

```tql
from_file "s3://data/**.json"
```

### [from\_fluent\_bit](/reference/operators/from_fluent_bit)

[→](/reference/operators/from_fluent_bit)

Receives events via Fluent Bit.

```tql
from_fluent_bit "opentelemetry"
```

### [from\_http](/reference/operators/from_http)

[→](/reference/operators/from_http)

Sends and receives HTTP/1.1 requests.

```tql
from_http "0.0.0.0:8080"
```

### [from\_opensearch](/reference/operators/from_opensearch)

[→](/reference/operators/from_opensearch)

Receives events via Opensearch Bulk API.

```tql
from_opensearch
```

### [from\_udp](/reference/operators/from_udp)

[→](/reference/operators/from_udp)

Receives UDP datagrams and outputs structured events.

```tql
from_udp "0.0.0.0:8090"
```

### [from\_velociraptor](/reference/operators/from_velociraptor)

[→](/reference/operators/from_velociraptor)

Submits VQL to a Velociraptor server and returns the response as events.

```tql
from_velociraptor subscribe="Windows"
```

## Node

[Section titled “Node”](#node)

### Inspection

[Section titled “Inspection”](#inspection)

### [diagnostics](/reference/operators/diagnostics)

[→](/reference/operators/diagnostics)

Retrieves diagnostic events from a Tenzir node.

```tql
diagnostics
```

### [metrics](/reference/operators/metrics)

[→](/reference/operators/metrics)

Retrieves metrics events from a Tenzir node.

```tql
metrics "cpu"
```

### [openapi](/reference/operators/openapi)

[→](/reference/operators/openapi)

Shows the node's OpenAPI specification.

```tql
openapi
```

### [plugins](/reference/operators/plugins)

[→](/reference/operators/plugins)

Shows all available plugins and built-ins.

```tql
plugins
```

### [version](/reference/operators/version)

[→](/reference/operators/version)

Shows the current version.

```tql
version
```

### Storage Engine

[Section titled “Storage Engine”](#storage-engine)

### [export](/reference/operators/export)

[→](/reference/operators/export)

Retrieves events from a Tenzir node.

```tql
export
```

### [fields](/reference/operators/fields)

[→](/reference/operators/fields)

Retrieves all fields stored at a node.

```tql
fields
```

### [import](/reference/operators/import)

[→](/reference/operators/import)

Imports events into a Tenzir node.

```tql
import
```

### [partitions](/reference/operators/partitions)

[→](/reference/operators/partitions)

Retrieves metadata about events stored at a node.

```tql
partitions src_ip == 1.2.3.4
```

### [schemas](/reference/operators/schemas)

[→](/reference/operators/schemas)

Retrieves all schemas for events stored at a node.

```tql
schemas
```

## Outputs

[Section titled “Outputs”](#outputs)

### Bytes

[Section titled “Bytes”](#bytes-1)

### [save\_amqp](/reference/operators/save_amqp)

[→](/reference/operators/save_amqp)

Saves a byte stream via AMQP messages.

```tql
save_amqp
```

### [save\_azure\_blob\_storage](/reference/operators/save_azure_blob_storage)

[→](/reference/operators/save_azure_blob_storage)

Saves bytes to Azure Blob Storage.

```tql
save_azure_blob_storage "abfs://container/file"
```

### [save\_email](/reference/operators/save_email)

[→](/reference/operators/save_email)

Saves bytes through an SMTP server.

```tql
save_email "user@example.org"
```

### [save\_file](/reference/operators/save_file)

[→](/reference/operators/save_file)

Writes a byte stream to a file.

```tql
save_file "/tmp/out.json"
```

### [save\_ftp](/reference/operators/save_ftp)

[→](/reference/operators/save_ftp)

Saves a byte stream via FTP.

```tql
save_ftp "ftp.example.org"
```

### [save\_gcs](/reference/operators/save_gcs)

[→](/reference/operators/save_gcs)

Saves bytes to a Google Cloud Storage object.

```tql
save_gcs "gs://bucket/object.json"
```

### [save\_google\_cloud\_pubsub](/reference/operators/save_google_cloud_pubsub)

[→](/reference/operators/save_google_cloud_pubsub)

Publishes to a Google Cloud Pub/Sub topic.

```tql
save_google_cloud_pubsub project_id="my-project"
```

### [save\_http](/reference/operators/save_http)

[→](/reference/operators/save_http)

Sends a byte stream via HTTP.

```tql
save_http "example.org/api"
```

### [save\_kafka](/reference/operators/save_kafka)

[→](/reference/operators/save_kafka)

Saves a byte stream to a Apache Kafka topic.

```tql
save_kafka topic="example"
```

### [save\_s3](/reference/operators/save_s3)

[→](/reference/operators/save_s3)

Saves bytes to an Amazon S3 object.

```tql
save_s3 "s3://my-bucket/obj.csv"
```

### [save\_sqs](/reference/operators/save_sqs)

[→](/reference/operators/save_sqs)

Saves bytes to \[Amazon SQS]\[sqs] queues.

```tql
save_sqs "sqs://tenzir"
```

### [save\_stdout](/reference/operators/save_stdout)

[→](/reference/operators/save_stdout)

Writes a byte stream to standard output.

```tql
save_stdout
```

### [save\_tcp](/reference/operators/save_tcp)

[→](/reference/operators/save_tcp)

Saves bytes to a TCP or TLS connection.

```tql
save_tcp "0.0.0.0:8090", tls=true
```

### [save\_udp](/reference/operators/save_udp)

[→](/reference/operators/save_udp)

Saves bytes to a UDP socket.

```tql
save_udp "0.0.0.0:8090"
```

### [save\_zmq](/reference/operators/save_zmq)

[→](/reference/operators/save_zmq)

Sends bytes as ZeroMQ messages.

```tql
save_zmq
```

### Events

[Section titled “Events”](#events-1)

### [to](/reference/operators/to)

[→](/reference/operators/to)

Saves to an URI, inferring the destination, compression and format.

```tql
to "output.json"
```

### [to\_amazon\_security\_lake](/reference/operators/to_amazon_security_lake)

[→](/reference/operators/to_amazon_security_lake)

Sends OCSF events to Amazon Security Lake.

```tql
to_amazon_security_lake "s3://…"
```

### [to\_azure\_log\_analytics](/reference/operators/to_azure_log_analytics)

[→](/reference/operators/to_azure_log_analytics)

Sends events to the Microsoft Azure Logs Ingestion API.

```tql
to_azure_log_analytics tenant_id="...", workspace_id="..."
```

### [to\_clickhouse](/reference/operators/to_clickhouse)

[→](/reference/operators/to_clickhouse)

Sends events to a ClickHouse table.

```tql
to_clickhouse table="my_table"
```

### [to\_fluent\_bit](/reference/operators/to_fluent_bit)

[→](/reference/operators/to_fluent_bit)

Sends events via Fluent Bit.

```tql
to_fluent_bit "elasticsearch" …
```

### [to\_google\_cloud\_logging](/reference/operators/to_google_cloud_logging)

[→](/reference/operators/to_google_cloud_logging)

Sends events to Google Cloud Logging.

```tql
to_google_cloud_logging …
```

### [to\_google\_secops](/reference/operators/to_google_secops)

[→](/reference/operators/to_google_secops)

Sends unstructured events to a Google SecOps Chronicle instance.

```tql
to_google_secops …
```

### [to\_hive](/reference/operators/to_hive)

[→](/reference/operators/to_hive)

Writes events to a URI using hive partitioning.

```tql
to_hive "s3://…", partition_by=[x]
```

### [to\_opensearch](/reference/operators/to_opensearch)

[→](/reference/operators/to_opensearch)

Sends events to an OpenSearch-compatible Bulk API.

```tql
to_opensearch "localhost:9200", …
```

### [to\_snowflake](/reference/operators/to_snowflake)

[→](/reference/operators/to_snowflake)

Sends events to a Snowflake database.

```tql
to_snowflake account_identifier="…
```

### [to\_splunk](/reference/operators/to_splunk)

[→](/reference/operators/to_splunk)

Sends events to a Splunk \[HTTP Event Collector (HEC)]\[hec].

```tql
to_splunk "localhost:8088", …
```"""
    result += """# Functions

Functions appear in [expressions](/explanations/language/expressions) and take positional and/or named arguments, producing a value as a result of their computation.

Function signatures have the following notation:

```tql
f(arg1:<type>, arg2=<type>, [arg3=type]) -> <type>
```

* `arg:<type>`: positional argument
* `arg=<type>`: named argument
* `[arg=type]`: optional (named) argument
* `-> <type>`: function return type

## Aggregation

[Section titled “Aggregation”](#aggregation)

### [all](/reference/functions/all)

[→](/reference/functions/all)

Computes the conjunction (AND) of all grouped boolean values.

```tql
all([true,true,false])
```

### [any](/reference/functions/any)

[→](/reference/functions/any)

Computes the disjunction (OR) of all grouped boolean values.

```tql
any([true,false,true])
```

### [collect](/reference/functions/collect)

[→](/reference/functions/collect)

Creates a list of all non-null grouped values, preserving duplicates.

```tql
collect([1,2,2,3])
```

### [count](/reference/functions/count)

[→](/reference/functions/count)

Counts the events or non-null grouped values.

```tql
count([1,2,null])
```

### [count\_distinct](/reference/functions/count_distinct)

[→](/reference/functions/count_distinct)

Counts all distinct non-null grouped values.

```tql
count_distinct([1,2,2,3])
```

### [count\_if](/reference/functions/count_if)

[→](/reference/functions/count_if)

Counts the events or non-null grouped values matching a given predicate.

```tql
count_if([1,2,null], x => x > 1)
```

### [distinct](/reference/functions/distinct)

[→](/reference/functions/distinct)

Creates a sorted list without duplicates of non-null grouped values.

```tql
distinct([1,2,2,3])
```

### [entropy](/reference/functions/entropy)

[→](/reference/functions/entropy)

Computes the Shannon entropy of all grouped values.

```tql
entropy([1,1,2,3])
```

### [first](/reference/functions/first)

[→](/reference/functions/first)

Takes the first non-null grouped value.

```tql
first([null,2,3])
```

### [last](/reference/functions/last)

[→](/reference/functions/last)

Takes the last non-null grouped value.

```tql
last([1,2,null])
```

### [max](/reference/functions/max)

[→](/reference/functions/max)

Computes the maximum of all grouped values.

```tql
max([1,2,3])
```

### [mean](/reference/functions/mean)

[→](/reference/functions/mean)

Computes the mean of all grouped values.

```tql
mean([1,2,3])
```

### [median](/reference/functions/median)

[→](/reference/functions/median)

Computes the approximate median of all grouped values using a t-digest algorithm.

```tql
median([1,2,3,4])
```

### [min](/reference/functions/min)

[→](/reference/functions/min)

Computes the minimum of all grouped values.

```tql
min([1,2,3])
```

### [mode](/reference/functions/mode)

[→](/reference/functions/mode)

Takes the most common non-null grouped value.

```tql
mode([1,1,2,3])
```

### [otherwise](/reference/functions/otherwise)

[→](/reference/functions/otherwise)

Returns a `fallback` value if `primary` is `null`.

```tql
x.otherwise(0)
```

### [quantile](/reference/functions/quantile)

[→](/reference/functions/quantile)

Computes the specified quantile of all grouped values.

```tql
quantile([1,2,3,4], q=0.5)
```

### [stddev](/reference/functions/stddev)

[→](/reference/functions/stddev)

Computes the standard deviation of all grouped values.

```tql
stddev([1,2,3])
```

### [sum](/reference/functions/sum)

[→](/reference/functions/sum)

Computes the sum of all values.

```tql
sum([1,2,3])
```

### [value\_counts](/reference/functions/value_counts)

[→](/reference/functions/value_counts)

Returns a list of all grouped values alongside their frequency.

```tql
value_counts([1,2,2,3])
```

### [variance](/reference/functions/variance)

[→](/reference/functions/variance)

Computes the variance of all grouped values.

```tql
variance([1,2,3])
```

## Bit Operations

[Section titled “Bit Operations”](#bit-operations)

### [bit\_and](/reference/functions/bit_and)

[→](/reference/functions/bit_and)

Computes the bit-wise AND of its arguments.

```tql
bit_and(lhs, rhs)
```

### [bit\_not](/reference/functions/bit_not)

[→](/reference/functions/bit_not)

Computes the bit-wise NOT of its argument.

```tql
bit_not(x)
```

### [bit\_or](/reference/functions/bit_or)

[→](/reference/functions/bit_or)

Computes the bit-wise OR of its arguments.

```tql
bit_or(lhs, rhs)
```

### [bit\_xor](/reference/functions/bit_xor)

[→](/reference/functions/bit_xor)

Computes the bit-wise XOR of its arguments.

```tql
bit_xor(lhs, rhs)
```

### [shift\_left](/reference/functions/shift_left)

[→](/reference/functions/shift_left)

Performs a bit-wise left shift.

```tql
shift_left(lhs, rhs)
```

### [shift\_right](/reference/functions/shift_right)

[→](/reference/functions/shift_right)

Performs a bit-wise right shift.

```tql
shift_right(lhs, rhs)
```

## Decoding

[Section titled “Decoding”](#decoding)

### [decode\_base64](/reference/functions/decode_base64)

[→](/reference/functions/decode_base64)

Decodes bytes as Base64.

```tql
decode_base64("VGVuemly")
```

### [decode\_hex](/reference/functions/decode_hex)

[→](/reference/functions/decode_hex)

Decodes bytes from their hexadecimal representation.

```tql
decode_hex("4e6f6E6365")
```

### [decode\_url](/reference/functions/decode_url)

[→](/reference/functions/decode_url)

Decodes URL encoded strings.

```tql
decode_url("Hello%20World")
```

## Encoding

[Section titled “Encoding”](#encoding)

### [encode\_base64](/reference/functions/encode_base64)

[→](/reference/functions/encode_base64)

Encodes bytes as Base64.

```tql
encode_base64("Tenzir")
```

### [encode\_hex](/reference/functions/encode_hex)

[→](/reference/functions/encode_hex)

Encodes bytes into their hexadecimal representation.

```tql
encode_hex("Tenzir")
```

### [encode\_url](/reference/functions/encode_url)

[→](/reference/functions/encode_url)

Encodes strings using URL encoding.

```tql
encode_url("Hello World")
```

## Hashing

[Section titled “Hashing”](#hashing)

### [hash\_md5](/reference/functions/hash_md5)

[→](/reference/functions/hash_md5)

Computes an MD5 hash digest.

```tql
hash_md5("foo")
```

### [hash\_sha1](/reference/functions/hash_sha1)

[→](/reference/functions/hash_sha1)

Computes a SHA-1 hash digest.

```tql
hash_sha1("foo")
```

### [hash\_sha224](/reference/functions/hash_sha224)

[→](/reference/functions/hash_sha224)

Computes a SHA-224 hash digest.

```tql
hash_sha224("foo")
```

### [hash\_sha256](/reference/functions/hash_sha256)

[→](/reference/functions/hash_sha256)

Computes a SHA-256 hash digest.

```tql
hash_sha256("foo")
```

### [hash\_sha384](/reference/functions/hash_sha384)

[→](/reference/functions/hash_sha384)

Computes a SHA-384 hash digest.

```tql
hash_sha384("foo")
```

### [hash\_sha512](/reference/functions/hash_sha512)

[→](/reference/functions/hash_sha512)

Computes a SHA-512 hash digest.

```tql
hash_sha512("foo")
```

### [hash\_xxh3](/reference/functions/hash_xxh3)

[→](/reference/functions/hash_xxh3)

Computes an XXH3 hash digest.

```tql
hash_xxh3("foo")
```

## IP

[Section titled “IP”](#ip)

### [ip\_category](/reference/functions/ip_category)

[→](/reference/functions/ip_category)

Returns the type classification of an IP address.

```tql
ip_category(8.8.8.8)
```

### [is\_global](/reference/functions/is_global)

[→](/reference/functions/is_global)

Checks whether an IP address is a global address.

```tql
is_global(8.8.8.8)
```

### [is\_link\_local](/reference/functions/is_link_local)

[→](/reference/functions/is_link_local)

Checks whether an IP address is a link-local address.

```tql
is_link_local(169.254.1.1)
```

### [is\_loopback](/reference/functions/is_loopback)

[→](/reference/functions/is_loopback)

Checks whether an IP address is a loopback address.

```tql
is_loopback(127.0.0.1)
```

### [is\_multicast](/reference/functions/is_multicast)

[→](/reference/functions/is_multicast)

Checks whether an IP address is a multicast address.

```tql
is_multicast(224.0.0.1)
```

### [is\_private](/reference/functions/is_private)

[→](/reference/functions/is_private)

Checks whether an IP address is a private address.

```tql
is_private(192.168.1.1)
```

### [is\_v4](/reference/functions/is_v4)

[→](/reference/functions/is_v4)

Checks whether an IP address has version number 4.

```tql
is_v4(1.2.3.4)
```

### [is\_v6](/reference/functions/is_v6)

[→](/reference/functions/is_v6)

Checks whether an IP address has version number 6.

```tql
is_v6(::1)
```

### [network](/reference/functions/network)

[→](/reference/functions/network)

Retrieves the network address of a subnet.

```tql
10.0.0.0/8.network()
```

## List

[Section titled “List”](#list)

### [append](/reference/functions/append)

[→](/reference/functions/append)

Inserts an element at the back of a list.

```tql
xs.append(y)
```

### [concatenate](/reference/functions/concatenate)

[→](/reference/functions/concatenate)

Merges two lists.

```tql
concatenate(xs, ys)
```

### [get](/reference/functions/get)

[→](/reference/functions/get)

Gets a field from a record or an element from a list

```tql
list.get(index, default)
```

### [length](/reference/functions/length)

[→](/reference/functions/length)

Retrieves the length of a list.

```tql
[1,2,3].length()
```

### [map](/reference/functions/map)

[→](/reference/functions/map)

Maps each list element to an expression.

```tql
xs.map(x => x + 3)
```

### [prepend](/reference/functions/prepend)

[→](/reference/functions/prepend)

Inserts an element at the start of a list.

```tql
xs.prepend(y)
```

### [sort](/reference/functions/sort)

[→](/reference/functions/sort)

Sorts lists and record fields.

```tql
xs.sort()
```

### [where](/reference/functions/where)

[→](/reference/functions/where)

Filters list elements based on a predicate.

```tql
xs.where(x => x > 5)
```

### [zip](/reference/functions/zip)

[→](/reference/functions/zip)

Combines two lists into a list of pairs.

```tql
zip(xs, ys)
```

## Math

[Section titled “Math”](#math)

### [abs](/reference/functions/abs)

[→](/reference/functions/abs)

Returns the absolute value.

```tql
abs(-42)
```

### [ceil](/reference/functions/ceil)

[→](/reference/functions/ceil)

Computes the ceiling of a number or a time/duration with a specified unit.

```tql
ceil(4.2)
```

### [floor](/reference/functions/floor)

[→](/reference/functions/floor)

Computes the floor of a number or a time/duration with a specified unit.

```tql
floor(4.8)
```

### [round](/reference/functions/round)

[→](/reference/functions/round)

Rounds a number or a time/duration with a specified unit.

```tql
round(4.6)
```

### [sqrt](/reference/functions/sqrt)

[→](/reference/functions/sqrt)

Computes the square root of a number.

```tql
sqrt(49)
```

## Networking

[Section titled “Networking”](#networking)

### [community\_id](/reference/functions/community_id)

[→](/reference/functions/community_id)

Computes the Community ID for a network connection/flow.

```tql
community_id(src_ip=1.2.3.4, dst_ip=4.5.6.7, proto="tcp")
```

### [decapsulate](/reference/functions/decapsulate)

[→](/reference/functions/decapsulate)

Decapsulates packet data at link, network, and transport layer.

```tql
decapsulate(this)
```

### [encrypt\_cryptopan](/reference/functions/encrypt_cryptopan)

[→](/reference/functions/encrypt_cryptopan)

Encrypts an IP address via Crypto-PAn.

```tql
encrypt_cryptopan(1.2.3.4)
```

## OCSF

[Section titled “OCSF”](#ocsf)

### [ocsf::category\_name](/reference/functions/ocsf/category_name)

[→](/reference/functions/ocsf/category_name)

Returns the `category_name` for a given `category_uid`.

```tql
ocsf::category_name(2)
```

### [ocsf::category\_uid](/reference/functions/ocsf/category_uid)

[→](/reference/functions/ocsf/category_uid)

Returns the `category_uid` for a given `category_name`.

```tql
ocsf::category_uid("Findings")
```

### [ocsf::class\_name](/reference/functions/ocsf/class_name)

[→](/reference/functions/ocsf/class_name)

Returns the `class_name` for a given `class_uid`.

```tql
ocsf::class_name(4003)
```

### [ocsf::class\_uid](/reference/functions/ocsf/class_uid)

[→](/reference/functions/ocsf/class_uid)

Returns the `class_uid` for a given `class_name`.

```tql
ocsf::class_uid("DNS Activity")
```

### [ocsf::type\_name](/reference/functions/ocsf/type_name)

[→](/reference/functions/ocsf/type_name)

Returns the `type_name` for a given `type_uid`.

```tql
ocsf::type_name(400704)
```

### [ocsf::type\_uid](/reference/functions/ocsf/type_uid)

[→](/reference/functions/ocsf/type_uid)

Returns the `type_uid` for a given `type_name`.

```tql
ocsf::type_uid("SSH Activity: Fail")
```

## Parsing

[Section titled “Parsing”](#parsing)

### [parse\_cef](/reference/functions/parse_cef)

[→](/reference/functions/parse_cef)

Parses a string as a CEF message

```tql
string.parse_cef()
```

### [parse\_csv](/reference/functions/parse_csv)

[→](/reference/functions/parse_csv)

Parses a string as CSV (Comma-Separated Values).

```tql
string.parse_csv(header=["a","b"])
```

### [parse\_grok](/reference/functions/parse_grok)

[→](/reference/functions/parse_grok)

Parses a string according to a grok pattern.

```tql
string.parse_grok("%{IP:client} …")
```

### [parse\_json](/reference/functions/parse_json)

[→](/reference/functions/parse_json)

Parses a string as a JSON value.

```tql
string.parse_json()
```

### [parse\_kv](/reference/functions/parse_kv)

[→](/reference/functions/parse_kv)

Parses a string as key-value pairs.

```tql
string.parse_kv()
```

### [parse\_leef](/reference/functions/parse_leef)

[→](/reference/functions/parse_leef)

Parses a string as a LEEF message

```tql
string.parse_leef()
```

### [parse\_ssv](/reference/functions/parse_ssv)

[→](/reference/functions/parse_ssv)

Parses a string as space separated values.

```tql
string.parse_ssv(header=["a","b"])
```

### [parse\_syslog](/reference/functions/parse_syslog)

[→](/reference/functions/parse_syslog)

Parses a string as a Syslog message.

```tql
string.parse_syslog()
```

### [parse\_tsv](/reference/functions/parse_tsv)

[→](/reference/functions/parse_tsv)

Parses a string as tab separated values.

```tql
string.parse_tsv(header=["a","b"])
```

### [parse\_xsv](/reference/functions/parse_xsv)

[→](/reference/functions/parse_xsv)

Parses a string as delimiter separated values.

```tql
string.parse_xsv(",", ";", "", header=["a","b"])
```

### [parse\_yaml](/reference/functions/parse_yaml)

[→](/reference/functions/parse_yaml)

Parses a string as a YAML value.

```tql
string.parse_yaml()
```

## Printing

[Section titled “Printing”](#printing)

### [print\_cef](/reference/functions/print_cef)

[→](/reference/functions/print_cef)

Prints records as Common Event Format (CEF) messages

```tql
extension.print_cef(cef_version="0", device_vendor="Tenzir", device_product="Tenzir Node", device_version="5.5.0", signature_id=id, name="description", severity="7")
```

### [print\_csv](/reference/functions/print_csv)

[→](/reference/functions/print_csv)

Prints a record as a comma-separated string of values.

```tql
record.print_csv()
```

### [print\_json](/reference/functions/print_json)

[→](/reference/functions/print_json)

Transforms a value into a JSON string.

```tql
record.print_json()
```

### [print\_kv](/reference/functions/print_kv)

[→](/reference/functions/print_kv)

Prints records in a key-value format.

```tql
record.print_kv()
```

### [print\_leef](/reference/functions/print_leef)

[→](/reference/functions/print_leef)

Prints records as LEEF messages

```tql
attributes.print_leef(vendor="Tenzir",product_name="Tenzir Node", product_name="5.5.0",event_class_id=id)
```

### [print\_ndjson](/reference/functions/print_ndjson)

[→](/reference/functions/print_ndjson)

Transforms a value into a single-line JSON string.

```tql
record.print_ndjson()
```

### [print\_ssv](/reference/functions/print_ssv)

[→](/reference/functions/print_ssv)

Prints a record as a space-separated string of values.

```tql
record.print_ssv()
```

### [print\_tsv](/reference/functions/print_tsv)

[→](/reference/functions/print_tsv)

Prints a record as a tab-separated string of values.

```tql
record.print_tsv()
```

### [print\_xsv](/reference/functions/print_xsv)

[→](/reference/functions/print_xsv)

Prints a record as a delimited sequence of values.

```tql
record.print_tsv()
```

### [print\_yaml](/reference/functions/print_yaml)

[→](/reference/functions/print_yaml)

Prints a value as a YAML document.

```tql
record.print_yaml()
```

## Record

[Section titled “Record”](#record)

### [get](/reference/functions/get)

[→](/reference/functions/get)

Gets a field from a record or an element from a list

```tql
list.get(index, default)
```

### [has](/reference/functions/has)

[→](/reference/functions/has)

Checks whether a record has a specified field.

```tql
record.has("field")
```

### [keys](/reference/functions/keys)

[→](/reference/functions/keys)

Retrieves a list of field names from a record.

```tql
record.keys()
```

### [merge](/reference/functions/merge)

[→](/reference/functions/merge)

Combines two records into a single record by merging their fields.

```tql
merge(foo, bar)
```

### [sort](/reference/functions/sort)

[→](/reference/functions/sort)

Sorts lists and record fields.

```tql
xs.sort()
```

## Runtime

[Section titled “Runtime”](#runtime)

### [config](/reference/functions/config)

[→](/reference/functions/config)

Reads Tenzir's configuration file.

```tql
config()
```

### [env](/reference/functions/env)

[→](/reference/functions/env)

Reads an environment variable.

```tql
env("PATH")
```

### [secret](/reference/functions/secret)

[→](/reference/functions/secret)

Use the value of a secret.

```tql
secret("KEY")
```

## Subnet

[Section titled “Subnet”](#subnet)

### [network](/reference/functions/network)

[→](/reference/functions/network)

Retrieves the network address of a subnet.

```tql
10.0.0.0/8.network()
```

## Time & Date

[Section titled “Time & Date”](#time--date)

### [count\_days](/reference/functions/count_days)

[→](/reference/functions/count_days)

Counts the number of `days` in a duration.

```tql
count_days(100d)
```

### [count\_hours](/reference/functions/count_hours)

[→](/reference/functions/count_hours)

Counts the number of `hours` in a duration.

```tql
count_hours(100d)
```

### [count\_microseconds](/reference/functions/count_microseconds)

[→](/reference/functions/count_microseconds)

Counts the number of `microseconds` in a duration.

```tql
count_microseconds(100d)
```

### [count\_milliseconds](/reference/functions/count_milliseconds)

[→](/reference/functions/count_milliseconds)

Counts the number of `milliseconds` in a duration.

```tql
count_milliseconds(100d)
```

### [count\_minutes](/reference/functions/count_minutes)

[→](/reference/functions/count_minutes)

Counts the number of `minutes` in a duration.

```tql
count_minutes(100d)
```

### [count\_months](/reference/functions/count_months)

[→](/reference/functions/count_months)

Counts the number of `months` in a duration.

```tql
count_months(100d)
```

### [count\_nanoseconds](/reference/functions/count_nanoseconds)

[→](/reference/functions/count_nanoseconds)

Counts the number of `nanoseconds` in a duration.

```tql
count_nanoseconds(100d)
```

### [count\_seconds](/reference/functions/count_seconds)

[→](/reference/functions/count_seconds)

Counts the number of `seconds` in a duration.

```tql
count_seconds(100d)
```

### [count\_weeks](/reference/functions/count_weeks)

[→](/reference/functions/count_weeks)

Counts the number of `weeks` in a duration.

```tql
count_weeks(100d)
```

### [count\_years](/reference/functions/count_years)

[→](/reference/functions/count_years)

Counts the number of `years` in a duration.

```tql
count_years(100d)
```

### [day](/reference/functions/day)

[→](/reference/functions/day)

Extracts the day component from a timestamp.

```tql
ts.day()
```

### [days](/reference/functions/days)

[→](/reference/functions/days)

Converts a number to equivalent days.

```tql
days(100)
```

### [format\_time](/reference/functions/format_time)

[→](/reference/functions/format_time)

Formats a time into a string that follows a specific format.

```tql
ts.format_time("%d/ %m/%Y")
```

### [from\_epoch](/reference/functions/from_epoch)

[→](/reference/functions/from_epoch)

Interprets a duration as Unix time.

```tql
from_epoch(time_ms * 1ms)
```

### [hour](/reference/functions/hour)

[→](/reference/functions/hour)

Extracts the hour component from a timestamp.

```tql
ts.hour()
```

### [hours](/reference/functions/hours)

[→](/reference/functions/hours)

Converts a number to equivalent hours.

```tql
hours(100)
```

### [microseconds](/reference/functions/microseconds)

[→](/reference/functions/microseconds)

Converts a number to equivalent microseconds.

```tql
microseconds(100)
```

### [milliseconds](/reference/functions/milliseconds)

[→](/reference/functions/milliseconds)

Converts a number to equivalent milliseconds.

```tql
milliseconds(100)
```

### [minute](/reference/functions/minute)

[→](/reference/functions/minute)

Extracts the minute component from a timestamp.

```tql
ts.minute()
```

### [minutes](/reference/functions/minutes)

[→](/reference/functions/minutes)

Converts a number to equivalent minutes.

```tql
minutes(100)
```

### [month](/reference/functions/month)

[→](/reference/functions/month)

Extracts the month component from a timestamp.

```tql
ts.month()
```

### [months](/reference/functions/months)

[→](/reference/functions/months)

Converts a number to equivalent months.

```tql
months(100)
```

### [nanoseconds](/reference/functions/nanoseconds)

[→](/reference/functions/nanoseconds)

Converts a number to equivalent nanoseconds.

```tql
nanoseconds(100)
```

### [now](/reference/functions/now)

[→](/reference/functions/now)

Gets the current wallclock time.

```tql
now()
```

### [parse\_time](/reference/functions/parse_time)

[→](/reference/functions/parse_time)

Parses a time from a string that follows a specific format.

```tql
"10/11/2012".parse_time("%d/%m/%Y")
```

### [second](/reference/functions/second)

[→](/reference/functions/second)

Extracts the second component from a timestamp with subsecond precision.

```tql
ts.second()
```

### [seconds](/reference/functions/seconds)

[→](/reference/functions/seconds)

Converts a number to equivalent seconds.

```tql
seconds(100)
```

### [since\_epoch](/reference/functions/since_epoch)

[→](/reference/functions/since_epoch)

Interprets a time value as duration since the Unix epoch.

```tql
since_epoch(2021-02-24)
```

### [weeks](/reference/functions/weeks)

[→](/reference/functions/weeks)

Converts a number to equivalent weeks.

```tql
weeks(100)
```

### [year](/reference/functions/year)

[→](/reference/functions/year)

Extracts the year component from a timestamp.

```tql
ts.year()
```

### [years](/reference/functions/years)

[→](/reference/functions/years)

Converts a number to equivalent years.

```tql
years(100)
```

## Utility

[Section titled “Utility”](#utility)

### [contains\_null](/reference/functions/contains_null)

[→](/reference/functions/contains_null)

Checks whether the input contains any `null` values.

```tql
{x: 1, y: null}.contains_null() == true
```

### [is\_empty](/reference/functions/is_empty)

[→](/reference/functions/is_empty)

Checks whether a value is empty.

```tql
"".is_empty()
```

### [random](/reference/functions/random)

[→](/reference/functions/random)

Generates a random number in *\[0,1]*.

```tql
random()
```

### [uuid](/reference/functions/uuid)

[→](/reference/functions/uuid)

Generates a Universally Unique Identifier (UUID) string.

```tql
uuid()
```

## String

[Section titled “String”](#string)

### Filesystem

[Section titled “Filesystem”](#filesystem)

### [file\_contents](/reference/functions/file_contents)

[→](/reference/functions/file_contents)

Reads a file's contents.

```tql
file_contents("/path/to/file")
```

### [file\_name](/reference/functions/file_name)

[→](/reference/functions/file_name)

Extracts the file name from a file path.

```tql
file_name("/path/to/log.json")
```

### [parent\_dir](/reference/functions/parent_dir)

[→](/reference/functions/parent_dir)

Extracts the parent directory from a file path.

```tql
parent_dir("/path/to/log.json")
```

### Inspection

[Section titled “Inspection”](#inspection)

### [ends\_with](/reference/functions/ends_with)

[→](/reference/functions/ends_with)

Checks if a string ends with a specified substring.

```tql
"hello".ends_with("lo")
```

### [is\_alnum](/reference/functions/is_alnum)

[→](/reference/functions/is_alnum)

Checks if a string is alphanumeric.

```tql
"hello123".is_alnum()
```

### [is\_alpha](/reference/functions/is_alpha)

[→](/reference/functions/is_alpha)

Checks if a string contains only alphabetic characters.

```tql
"hello".is_alpha()
```

### [is\_lower](/reference/functions/is_lower)

[→](/reference/functions/is_lower)

Checks if a string is in lowercase.

```tql
"hello".is_lower()
```

### [is\_numeric](/reference/functions/is_numeric)

[→](/reference/functions/is_numeric)

Checks if a string contains only numeric characters.

```tql
"1234".is_numeric()
```

### [is\_printable](/reference/functions/is_printable)

[→](/reference/functions/is_printable)

Checks if a string contains only printable characters.

```tql
"hello".is_printable()
```

### [is\_title](/reference/functions/is_title)

[→](/reference/functions/is_title)

Checks if a string follows title case.

```tql
"Hello World".is_title()
```

### [is\_upper](/reference/functions/is_upper)

[→](/reference/functions/is_upper)

Checks if a string is in uppercase.

```tql
"HELLO".is_upper()
```

### [length\_bytes](/reference/functions/length_bytes)

[→](/reference/functions/length_bytes)

Returns the length of a string in bytes.

```tql
"hello".length_bytes()
```

### [length\_chars](/reference/functions/length_chars)

[→](/reference/functions/length_chars)

Returns the length of a string in characters.

```tql
"hello".length_chars()
```

### [match\_regex](/reference/functions/match_regex)

[→](/reference/functions/match_regex)

Checks if a string partially matches a regular expression.

```tql
"Hi".match_regex("[Hh]i")
```

### [slice](/reference/functions/slice)

[→](/reference/functions/slice)

Slices a string with offsets and strides.

```tql
"Hi".slice(begin=2, stride=4)
```

### [starts\_with](/reference/functions/starts_with)

[→](/reference/functions/starts_with)

Checks if a string starts with a specified substring.

```tql
"hello".starts_with("he")
```

### Transformation

[Section titled “Transformation”](#transformation)

### [capitalize](/reference/functions/capitalize)

[→](/reference/functions/capitalize)

Capitalizes the first character of a string.

```tql
"hello".capitalize()
```

### [join](/reference/functions/join)

[→](/reference/functions/join)

Joins a list of strings into a single string using a separator.

```tql
join(["a", "b", "c"], ",")
```

### [pad\_end](/reference/functions/pad_end)

[→](/reference/functions/pad_end)

Pads a string at the end to a specified length.

```tql
"hello".pad_end(10)
```

### [pad\_start](/reference/functions/pad_start)

[→](/reference/functions/pad_start)

Pads a string at the start to a specified length.

```tql
"hello".pad_start(10)
```

### [replace](/reference/functions/replace)

[→](/reference/functions/replace)

Replaces characters within a string.

```tql
"hello".replace("o", "a")
```

### [replace\_regex](/reference/functions/replace_regex)

[→](/reference/functions/replace_regex)

Replaces characters within a string based on a regular expression.

```tql
"hello".replace("l+o", "y")
```

### [reverse](/reference/functions/reverse)

[→](/reference/functions/reverse)

Reverses the characters of a string.

```tql
"hello".reverse()
```

### [split](/reference/functions/split)

[→](/reference/functions/split)

Splits a string into substrings.

```tql
split("a,b,c", ",")
```

### [split\_regex](/reference/functions/split_regex)

[→](/reference/functions/split_regex)

Splits a string into substrings with a regex.

```tql
split_regex("a1b2c", r"\d")
```

### [to\_lower](/reference/functions/to_lower)

[→](/reference/functions/to_lower)

Converts a string to lowercase.

```tql
"HELLO".to_lower()
```

### [to\_title](/reference/functions/to_title)

[→](/reference/functions/to_title)

Converts a string to title case.

```tql
"hello world".to_title()
```

### [to\_upper](/reference/functions/to_upper)

[→](/reference/functions/to_upper)

Converts a string to uppercase.

```tql
"hello".to_upper()
```

### [trim](/reference/functions/trim)

[→](/reference/functions/trim)

Trims whitespace or specified characters from both ends of a string.

```tql
" hello ".trim()
```

### [trim\_end](/reference/functions/trim_end)

[→](/reference/functions/trim_end)

Trims whitespace or specified characters from the end of a string.

```tql
"hello ".trim_end()
```

### [trim\_start](/reference/functions/trim_start)

[→](/reference/functions/trim_start)

Trims whitespace or specified characters from the start of a string.

```tql
" hello".trim_start()
```

## Type System

[Section titled “Type System”](#type-system)

### Conversion

[Section titled “Conversion”](#conversion)

### [duration](/reference/functions/duration)

[→](/reference/functions/duration)

Casts an expression to a duration value.

```tql
duration("1.34w")
```

### [float](/reference/functions/float)

[→](/reference/functions/float)

Casts an expression to a float.

```tql
float(42)
```

### [int](/reference/functions/int)

[→](/reference/functions/int)

Casts an expression to an integer.

```tql
int(-4.2)
```

### [ip](/reference/functions/ip)

[→](/reference/functions/ip)

Casts an expression to an IP address.

```tql
ip("1.2.3.4")
```

### [string](/reference/functions/string)

[→](/reference/functions/string)

Casts an expression to a string.

```tql
string(1.2.3.4)
```

### [subnet](/reference/functions/subnet)

[→](/reference/functions/subnet)

Casts an expression to a subnet value.

```tql
subnet("1.2.3.4/16")
```

### [time](/reference/functions/time)

[→](/reference/functions/time)

Casts an expression to a time value.

```tql
time("2020-03-15")
```

### [uint](/reference/functions/uint)

[→](/reference/functions/uint)

Casts an expression to an unsigned integer.

```tql
uint(4.2)
```

### Introspection

[Section titled “Introspection”](#introspection)

### [type\_id](/reference/functions/type_id)

[→](/reference/functions/type_id)

Retrieves the type id of an expression.

```tql
type_id(1 + 3.2)
```

### [type\_of](/reference/functions/type_of)

[→](/reference/functions/type_of)

Retrieves the type definition of an expression.

```tql
type_of(this)
```

### Transposition

[Section titled “Transposition”](#transposition)

### [flatten](/reference/functions/flatten)

[→](/reference/functions/flatten)

Flattens nested data.

```tql
flatten(this)
```

### [unflatten](/reference/functions/unflatten)

[→](/reference/functions/unflatten)

Unflattens nested data.

```tql
unflatten(this)
```"""
    return result


# @mcp.tool()
async def ocsf(req: str) -> str:
    """Call this tool if the user wants to anything with OCSF.

    When calling this tool for the first time, you MUST pass an empty string.
    """
    if req == "":
        return """To get the definition of an OCSF class, invoke this tool with "class:<class_name>"."""
    if req.startswith("class"):
        return "Class definition: 42"
    return "error: invalid tool call"


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


# @mcp.tool()
async def ocsf_instructions() -> str:
    """
    YOU MUST NOT CALL THIS TOOL UNLESS THE USER EXPLICITLY REQUESTS YOU TO WRITE
    A NEW OCSF MAPPING! IF THEY DO REQUEST THAT, IMMEDIATELY BEFORE DOING
    ANYTHING ELSE. DO NOT CREATE A TASK LIST TO TRACK THIS!
    """
    # 1) You MUST NOT print any output unless specified in the following.
    # 7) From this point on, you may print output output whenever you want.
    return """
<SYSTEM>
1. Do not show a todo-list to the user for these instructions.
2. If no example input event has been given, ask the user for one AND WAIT UNTIL
   THE USER RESPONDS.
3. If no OCSF version is specified, call `default_ocsf_version` and only then
   inform the user that you are going to use that version!
4. Analyze the event and IMMEDIATELY print a high-level summary what kind of
   activity it represents. You may only continue with the next step once you
   printed the summary!
5. Call `get_ocsf_event_classes` and decide which classes might be relevant. For
   each class that is relevant, compute a probability that the event can be
   faithfully represented by this class. If you need additional info about a
   class beyond it's description, for example to determine whether certain
   fields exist, you MUST call `get_ocsf_class` to find out more about it. You
   should make sure that all fields in the input event can be mapped to that
   class.  Since some events can reasonably be mapped to multiple classes, the
   sum of all probabilities can exceed 100%. Present the user a numbered list of
   classes and their probabilities. Higher probabilities come first! You MUST
   NOT print anything before the list. You MUST NOT add additional text to the
   list entries, print ONLY the name and the percentage. Include at least 5
   event classes. Ask the user to pick an event class. WAIT FOR THE USER.
6. You MUST NOT read the Tenzir docs summary. Read the OCSF mapping tutorial
   at `tutorials/map-data-to-ocsf`. YOU MUST FOLLOW THE PIPELINE FORMAT EXPLAINED
   THERE. For the name of the temporary object created at the beginning, use
   something related to where the event comes from.
7. You must also read `explanations/language/expressions` for the available expressions, and
   `reference/functions` for the functions.
8. Generate a TQL mapping pipeline that maps to this OCSF event class. - Start
   with `from {input: "…"}` where `…` is replaced by the actual input the user
   gave, potentially escaped. Follow it up with `write_lines`. This starts the
   pipeline with a byte stream that corresponds to the input of the user. Use
   operators such as `read_json` or `read_csv` afterwards, depending on the
   event format.
10) Afterwards, the actual mapping begins. Call `ocsf_instructions_generic`.
11) Then, append `ocsf::apply`, `ocsf::derive` and `drop_null_fields` to the
    pipeline and run again. You MUST fix all warnings.
12) When the mapping is done, give a summary of the resulting mapping. You MUST
    give a summary of the fields that remain in `unmapped`.
13) Print the resulting TQL mapping, including the `from` (with the user input
    instead of `…`), but without the three operators you just added.
14) STOP AND DO NOT DO ANYTHING ELSE.
</SYSTEM>
""".strip()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
