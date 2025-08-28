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
    Execute a TQL pipeline. You MUST use this instead of calling `tenzir` directly.

    Args:
        pipeline: The pipeline definition to execute
        is_file: Whether `pipeline` is a path to a file containing the definition
        timeout: Execution timeout in seconds (default: 30)
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
async def ocsf_mapping_examples() -> str:
    """Returns a few OCSF mappings examples following the best practices."""
    return """
## Complex OCSF Mapping Examples

### 1. Suricata DNS Activity Mapping
```tql
let $rcode_id = {
  NOERROR: 0,
  FORMERROR: 1,
  SERVERROR: 2,
  NXDOMAIN: 3,
  NOTIMP: 4,
  REFUSED: 5,
  YXDOMAIN: 6,
  YXRRSET: 7,
  NXRRSET: 8,
  NOTAUTH: 9,
  NOTZONE: 10,
  DSOTYPENI: 11,
  BADSIG_VERS: 16,
  BADKEY: 17,
  BADTIME: 18,
  BADMODE: 19,
  BADNAME: 20,
  BADALG: 21,
  BADTRUNC: 22,
  BADCOOKIE: 23,
}
let $rcode = {
  NOERROR: "NoError",
  FORMERROR: "FormError",
  SERVERROR: "ServError",
  NXDOMAIN: "NXDomain",
  NOTIMP: "NotImp",
  REFUSED: "Refused",
  YXDOMAIN: "YXDomain",
  YXRRSET: "YXRRSet",
  NXRRSET: "NXRRSet",
  NOTAUTH: "NotAuth",
  NOTZONE: "NotZone",
  DSOTYPENI: "DSOTYPENI",
  BADSIG_VERS: "BADSIG_VERS",
  BADKEY: "BADKEY",
  BADTIME: "BADTIME",
  BADMODE: "BADMODE",
  BADNAME: "BADNAME",
  BADALG: "BADALG",
  BADTRUNC: "BADTRUNC",
  BADCOOKIE: "BADCOOKIE",
}
this = { suricata: this }
// Conditional query handling for different Suricata versions
has_query = false
has_response = false
if suricata.dns.has("queries") {
  // Version >=8 DNS query logs.
  ocsf.query = {
    hostname: suricata.dns.queries.first().rrname,
    type: suricata.dns.queries.first().rrtype,
  }
  has_query = true
} else {
  // Version <=7 DNS query logs.
  ocsf.query = {
    hostname: move suricata.dns.rrname,
    type: move suricata.dns.rrtype,
  }
  has_query = true
}
ocsf.answers = (move suricata.dns.answers).map(answer => {
  type: answer.rrtype,
  rdata: answer.rdata,
  ttl: answer.ttl,
})
has_response = ocsf.answers != null and ocsf.answers.length() > 0
// Dynamic activity ID based on request/response presence
if (has_query and has_response) {
  activity_id = 6
  type_uid = 400306
} else if (has_query) {
  activity_id = 1
  type_uid = 400301
} else if (has_response) {
  activity_id = 2
  type_uid = 400302
}
ocsf.type_uid = type_uid
ocsf.activity_id = activity_id
ocsf.rcode_id = $rcode_id.get(suricata.dns.rcode, 99)
ocsf.rcode = $rcode.get(move suricata.dns.rcode, suricata.dns.rcode)
```

### 2. Zeek Connection State Complex Mapping
```tql
// Complex connection state mapping with multiple lookups
let $conn_states = {
  // S0 means only a SYN seen and S1 the full handshake.
  S0: 1,
  S1: 1,
  // Only SF means Close.
  SF: 2,
  // The RST* states imply connection reset.
  RSTO: 3,
  RSTOH: 3,
  RSTOS0: 3,
  RSTR: 3,
  RSTRH: 3,
  // SH, SHR, S2, and S3 correspond to one-sided closure
  S2: 4,
  S3: 4,
  SH: 4,
  SHR: 4,
  // Only REJ is rejection at the beginning of the connection.
  REJ: 5,
  // Connections Zeek couldn't classify.
  OTH: 6,
}
let $activity_names = [
  "Unknown",
  "Open",
  "Close",
  "Reset",
  "Fail",
  "Refuse",
  "Traffic",
  "Listen",
  "Other",
]
let $proto_nums = {
  tcp: 6,
  udp: 17,
  icmp: 1,
  icmpv6: 58,
  ipv6: 41,
}
this = { zeek: this }
ocsf.activity_id = $conn_states[zeek.conn_state]? else 6
ocsf.activity_name = $activity_names[ocsf.activity_id]? else "Other"
// Complex direction determination
if zeek.local_orig? != null and zeek.local_resp? != null {
  if zeek.local_orig and zeek.local_resp {
    ocsf.connection_info.direction = "Lateral"
    ocsf.connection_info.direction_id = 3
  } else if zeek.local_orig {
    ocsf.connection_info.direction = "Outbound"
    ocsf.connection_info.direction_id = 2
  } else if zeek.local_resp {
    ocsf.connection_info.direction = "Inbound"
    ocsf.connection_info.direction_id = 1
  } else {
    ocsf.connection_info.direction = "Unknown"
    ocsf.connection_info.direction_id = 0
  }
  drop zeek.local_orig, zeek.local_resp
}
// Protocol version detection
if zeek.id.orig_h.is_v6() or zeek.id.resp_h.is_v6() {
  ocsf.connection_info.protocol_ver_id = 6
} else {
  ocsf.connection_info.protocol_ver_id = 4
}
```

### 3. Suricata SMB Activity with Complex File Handling
```tql
let $activity_id = {
  FILE_SUPERSEDE: 1,
  FILE_OPEN: 2,
  FILE_CREATE: 3,
  FILE_OPEN_IF: 4,
  FILE_OVERWRITE: 5,
  FILE_OVERWRITE_IF: 6,
}
let $activity_name = {
  FILE_SUPERSEDE: "File Supersede",
  FILE_OPEN: "File Open",
  FILE_CREATE: "File Create",
  FILE_OPEN_IF: "File Open If",
  FILE_OVERWRITE: "File Overwrite",
  FILE_OVERWRITE_IF: "File Overwrite If",
}
this = { suricata: this }
ocsf.activity_id = $activity_id.get(suricata.smb.disposition, 99)
ocsf.activity_name = $activity_name.get(move suricata.smb.disposition, move suricata.smb.command)
// Complex status code handling
if suricata.smb.status_code == "0x0" {
  ocsf.status_id = 1
  ocsf.status = "Success"
} else {
  ocsf.status_id = 99
  ocsf.status = move suricata.smb.status
}
drop suricata.smb.status_code
// Conditional file information
if suricata.smb.filename != null {
  ocsf.file = {
    type_id: 0,
    name: move suricata.smb.filename,
    created_time: (move suricata.smb.created).milliseconds().from_epoch(),
    modified_time: (move suricata.smb.modified).milliseconds().from_epoch(),
    accessed_time: (move suricata.smb.accessed).milliseconds().from_epoch(),
  }
} else {
  ocsf.file = null
}
```

### 4. Zeek DHCP Multi-Message Mapping
```tql
let $msg_types = {
  DISCOVER: 1,
  OFFER: 2,
  REQUEST: 3,
  DECLINE: 4,
  ACK: 5,
  NAK: 6,
  RELEASE: 7,
  INFORM: 8,
}
this = { zeek: this }
// Unroll array to create separate events for each DHCP message type
unroll zeek.msg_types
ocsf.activity_id = $msg_types[zeek.msg_types] else 0
if ocsf.activity_id == 0 {
  ocsf.activity_name = "Other"
} else {
  ocsf.activity_name = to_title(move zeek.msg_types)
}
// Complex endpoint mapping with fallbacks
ocsf.src_endpoint = {
  hostname: move zeek.host_name?,
  // client_addr is preferred, fallback to assigned_addr
  ip: move zeek.client_addr? else zeek.assigned_addr?,
  domain: move zeek.client_fqdn?,
  mac: move zeek.mac?,
}
// Protocol version detection with null handling
if zeek.id?.resp_h? == null {
  ocsf.connection_info.protocol_ver_id = 0
} else if zeek.id.resp_h.is_v6() {
  ocsf.connection_info.protocol_ver_id = 6
} else {
  ocsf.connection_info.protocol_ver_id = 4
}
```

### 5. Complex Severity and Status Mapping (Suricata Alert)
```tql
this = { suricata: this }
// Complex severity mapping with fallback
if suricata.alert.severity == null {
  ocsf.severity_id = 0
} else if suricata.alert.severity == 1 {
  ocsf.severity_id = 4
} else if suricata.alert.severity == 2 {
  ocsf.severity_id = 3
} else if suricata.alert.severity == 3 {
  ocsf.severity_id = 2
}
drop suricata.alert.severity
// Evidence array construction
ocsf.evidences = [{
  src_endpoint: {
    ip: move suricata.src_ip,
    port: move suricata.src_port,
  },
  dst_endpoint: {
    ip: move suricata.dest_ip,
    port: move suricata.dest_port,
  },
}]
// Finding info object with proper UID conversion
ocsf.finding_info = {
  uid: (move suricata.flow_id).string(),
  title: move suricata.alert.category,
  desc: move suricata.alert.signature,
}
```

### Key Patterns in Complex Mappings:
1. **Lookup Tables**: Use `let` to define mapping dictionaries for codes, statuses, activities
2. **Conditional Logic**: Complex `if/else` chains for dynamic field assignment
3. **Fallback Values**: Use `else` operators for graceful degradation
4. **Array Operations**: `.map()`, `.first()`, `unroll` for array transformations
5. **Move vs Copy**: Strategic use of `move` to prevent duplication in `unmapped`
6. **Null Handling**: Check for null values before processing with `?` operator
7. **Type Conversions**: `.string()`, `.milliseconds().from_epoch()`, `int()` for proper typing
8. **Complex Object Construction**: Nested objects with conditional fields
9. **Protocol Detection**: IP version detection patterns
10. **Status Mapping**: Multi-level status code translation
"""


@mcp.tool()
async def tql_instructions(ocsf: bool) -> str:
    """VERY IMPORTANT: YOU MUST CALL THIS TOOL BEFORE YOU WRITE ANY TQL PIPELINES/MAPPINGS.

    Set `for_ocsf` to `true` if the user requested you to write a fresh, new OCSF mapping.
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
- REQUIRED: For parsing tasks, explore operators like read_grok, read_syslog, read_lines+parsing, from_file with pipeline
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
