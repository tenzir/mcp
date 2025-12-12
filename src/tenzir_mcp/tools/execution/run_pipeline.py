"""TQL pipeline execution tool."""

import asyncio
import time
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import BaseModel, Field

from tenzir_mcp.server import mcp

logger = get_logger(__name__)


class PipelineRequest(BaseModel):
    """Request model for pipeline execution."""

    pipeline: str = Field(..., description="TQL pipeline definition")
    is_file: bool = Field(..., description="Whether `pipeline` is a path to a file")
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

    def __init__(self, tenzir_binary: str = "tenzir") -> None:
        self.tenzir_binary = tenzir_binary

    async def execute_pipeline(self, request: PipelineRequest) -> PipelineResponse:
        """Execute a TQL pipeline."""
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
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=request.max_execution_time,
                )
            except asyncio.TimeoutError:  # noqa: UP041
                # asyncio.wait_for raises asyncio-specific TimeoutError
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
            error_msg = f"Pipeline execution failed: {e}"
            logger.error(error_msg)
            return PipelineResponse(
                success=False, output=error_msg, duration_seconds=execution_time
            )


# Global pipeline runner instance
pipeline_runner = TenzirPipelineRunner()


@mcp.tool(
    name="run_pipeline",
    tags={"execution"},
    annotations={
        "title": "Run TQL pipeline",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def run_pipeline(
    pipeline: Annotated[
        str, Field(description="TQL pipeline code or file path to execute")
    ],
    is_file: Annotated[
        bool,
        Field(
            description="Whether 'pipeline' is a file path (true) or inline code (false)"
        ),
    ],
    max_execution_time: Annotated[
        int,
        Field(
            default=30,
            ge=1,
            le=300,
            description="Maximum execution time in seconds",
        ),
    ],
) -> ToolResult:
    """Execute a TQL pipeline through the local `tenzir` binary.

    Use this tool to:
    - Test TQL code before adding it to a package
    - Debug pipeline behavior with sample data
    - Verify operator syntax and semantics
    - Iterate quickly on pipeline development

    The pipeline runs with diagnostics enabled, providing detailed error messages
    and warnings to help troubleshoot issues."""
    request = PipelineRequest(
        pipeline=pipeline,
        is_file=is_file,
        max_execution_time=max_execution_time,
    )

    response = await pipeline_runner.execute_pipeline(request)

    # Format as markdown
    status = "✓ Success" if response.success else "✗ Failed"
    content = f"**Status**: {status}\n**Duration**: {response.duration_seconds:.2f}s\n\n```\n{response.output}\n```"

    return ToolResult(
        content=content,  # Markdown formatted output
        structured_content={
            "success": response.success,
            "output": response.output,
            "duration_seconds": response.duration_seconds,
        },
    )
