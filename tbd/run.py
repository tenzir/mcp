#!/usr/bin/env python3
"""
Converts Claude Code conversation JSON output to a human-readable transcript.
Also processes .prompt files through Claude Code and generates transcripts.
"""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any


def format_timestamp(timestamp_ms: int) -> str:
    """Convert millisecond timestamp to human-readable format."""
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M:%S")


def format_tool_use(tool_use: dict[str, Any]) -> str:
    """Format a tool use call for display."""
    tool_name = tool_use.get("name", "unknown")
    tool_input = tool_use.get("input", {})

    # Format the tool input with full parameters
    if isinstance(tool_input, dict) and tool_input:
        params = []
        for key, value in tool_input.items():
            if isinstance(value, str):
                value_display = f"'{value}'"
            else:
                value_display = str(value)
            params.append(f"{key}={value_display}")

        params_str = ", ".join(params)
        return f"🔧 {tool_name}({params_str})"

    return f"🔧 {tool_name}()"


def format_content(content: list[dict[str, Any]]) -> str:
    """Format message content for display."""
    result = []

    for item in content:
        if item["type"] == "text":
            result.append(item["text"])
        elif item["type"] == "tool_use":
            result.append(format_tool_use(item))
        elif item["type"] == "tool_result":
            if item.get("is_error", False):
                result.append(f"❌ Error: {item['content']}")
            else:
                content_text = item["content"]
                result.append(f"✅ Result: {content_text}")

    return "\n".join(result)


def process_conversation(data: list[dict[str, Any]]) -> str:
    """Process the conversation data and return a formatted transcript."""
    transcript = []

    for entry in data:
        entry_type = entry.get("type", "")

        if entry_type == "system":
            if entry.get("subtype") == "init":
                transcript.append("=" * 60)
                transcript.append("🤖 CLAUDE CODE CONVERSATION")
                transcript.append("=" * 60)
                transcript.append(f"Session ID: {entry.get('session_id', 'unknown')}")
                transcript.append(f"Model: {entry.get('model', 'unknown')}")
                transcript.append(f"Working Directory: {entry.get('cwd', 'unknown')}")
                if entry.get("mcp_servers"):
                    servers = ", ".join(s["name"] for s in entry["mcp_servers"])
                    transcript.append(f"MCP Servers: {servers}")
                transcript.append("")
            continue

        elif entry_type == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])

            transcript.append("🤖 ASSISTANT:")
            formatted_content = format_content(content)
            if formatted_content:
                transcript.append(formatted_content)
            else:
                transcript.append("(no content)")

            # Add usage info if available
            usage = message.get("usage", {})
            if usage:
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                transcript.append(
                    f"   📊 Tokens: {input_tokens} in, {output_tokens} out"
                )

            transcript.append("")

        elif entry_type == "user":
            message = entry.get("message", {})
            content = message.get("content", [])

            transcript.append("👤 USER:")
            formatted_content = format_content(content)
            if formatted_content:
                transcript.append(formatted_content)
            else:
                transcript.append("(no content)")
            transcript.append("")

        elif entry_type == "result":
            transcript.append("📋 SESSION RESULT:")
            result_text = entry.get("result", "")
            if result_text:
                transcript.append(result_text)

            # Add cost and usage summary
            cost = entry.get("total_cost_usd", 0)
            if cost > 0:
                transcript.append(f"💰 Total Cost: ${cost:.4f}")

            duration = entry.get("duration_ms", 0)
            if duration > 0:
                transcript.append(f"⏱️  Duration: {duration}ms")

            # Add permission denials if any
            denials = entry.get("permission_denials", [])
            if denials:
                transcript.append("🚫 Permission Denials:")
                for denial in denials:
                    transcript.append(f"   - {denial['tool_name']}")

            transcript.append("")

    return "\n".join(transcript)


def process_json_content(content: str) -> str:
    """Process JSON content and return formatted transcript."""
    # Parse each line as a separate JSON object
    data = []
    for line in content.split("\n"):
        line = line.strip()
        if line:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse line: {line[:50]}... ({e})")

    return process_conversation(data)


def run_claude_on_txt_file_streaming(txt_file: str, output_file: str) -> bool:
    """Run claude command on a txt file and stream the transcript to output file."""
    try:
        # Read the input file
        with open(txt_file, encoding="utf-8") as f:
            txt_content = f.read()

        # Start the subprocess
        process = subprocess.Popen(
            [
                "claude",
                "--model",
                "sonnet",
                "--strict-mcp-config",
                "--mcp-config",
                "mcp-config.json",
                "--settings",
                "claude-settings.json",
                "--verbose",
                "--output-format",
                "stream-json",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Send input and close stdin
        process.stdin.write(txt_content)
        process.stdin.close()

        # Open output file for writing
        with open(output_file, "w", encoding="utf-8") as f:
            data = []

            # Read lines as they come
            for line in process.stdout:
                line = line.strip()
                if line:
                    try:
                        # Parse the JSON object
                        json_obj = json.loads(line)
                        data.append(json_obj)

                        # Process and write the current transcript
                        transcript = process_conversation(data)
                        f.seek(0)
                        f.truncate()
                        f.write(transcript)
                        f.flush()

                    except json.JSONDecodeError as e:
                        print(f"Warning: Could not parse line: {line[:50]}... ({e})")

        # Wait for process to complete
        return_code = process.wait()

        if return_code != 0:
            stderr_output = process.stderr.read()
            print(f"Error running claude on {txt_file}: {stderr_output}")
            return False

        return True

    except FileNotFoundError:
        print("Error: 'claude' command not found. Make sure Claude Code is installed and in PATH.")
        return False
    except Exception as e:
        print(f"Error running claude on {txt_file}: {e}")
        return False


def process_single_prompt_file(prompt_file: Path) -> tuple[str, bool, float]:
    """Process a single prompt file and return (filename, success, duration)."""
    start_time = time.time()
    output_file = prompt_file.with_suffix(".output")
    success = run_claude_on_txt_file_streaming(str(prompt_file), str(output_file))
    duration = time.time() - start_time
    return prompt_file.name, success, duration


def process_all_prompt_files():
    """Process all .prompt files in current directory through Claude and generate transcripts."""
    current_dir = Path.cwd()
    prompt_files = list(current_dir.glob("*.prompt"))

    if not prompt_files:
        print("No .prompt files found in current directory.")
        return

    print(f"Found {len(prompt_files)} .prompt files to process:")
    for prompt_file in prompt_files:
        print(f"  - {prompt_file.name}")
    print()

    print("Processing files in parallel...")

    # Track progress
    completed = 0
    total = len(prompt_files)
    successful = 0
    failed = 0
    total_duration = 0.0
    start_time = time.time()

    # Use ThreadPoolExecutor to process files in parallel
    with ThreadPoolExecutor(max_workers=min(len(prompt_files), 16)) as executor:
        # Submit all files for processing
        future_to_file = {
            executor.submit(process_single_prompt_file, prompt_file): prompt_file
            for prompt_file in prompt_files
        }

        # Process results as they complete
        for future in as_completed(future_to_file):
            filename, success, duration = future.result()
            completed += 1
            total_duration += duration
            if success:
                successful += 1
                output_name = filename.replace('.prompt', '.output')
                print(f"  ✅ {filename} → {output_name} ({duration:.1f}s) [{completed}/{total}]")
            else:
                failed += 1
                print(f"  ❌ Error processing {filename} ({duration:.1f}s) [{completed}/{total}]")

    # Final summary
    total_elapsed = time.time() - start_time
    print("\n📊 Summary:")
    print(f"  • Total files: {total}")
    print(f"  • Successful: {successful}")
    print(f"  • Failed: {failed}")
    print(f"  • Total processing time: {total_duration:.1f}s")
    print(f"  • Wall clock time: {total_elapsed:.1f}s")
    print(f"  • Average per file: {total_duration/total:.1f}s")
    if total_elapsed > 0:
        print(f"  • Parallelization efficiency: {total_duration/total_elapsed:.1f}x")
    print("\nDone processing all .prompt files.")


def main():
    """Main function to process JSON files or prompt files."""
    if len(sys.argv) == 1:
        # No arguments - process all .prompt files in current directory
        process_all_prompt_files()
    elif len(sys.argv) == 2:
        # One argument - process the specified JSON file
        json_file = sys.argv[1]

        try:
            # Read the JSON file
            with open(json_file, encoding="utf-8") as f:
                content = f.read().strip()

            # Process the conversation
            transcript = process_json_content(content)
            print(transcript)

        except FileNotFoundError:
            print(f"Error: File '{json_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing file: {e}")
            sys.exit(1)
    else:
        print("Usage:")
        print(
            "  python conversation_transcript.py                 # Process all .prompt files"
        )
        print(
            "  python conversation_transcript.py <json_file>     # Process specific JSON file"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
