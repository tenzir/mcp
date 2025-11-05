"""System prompts for the Tenzir MCP Server."""

from pathlib import Path


def load_system_prompt() -> str:
    """Load the system prompt from system.md."""
    prompt_file = Path(__file__).parent / "system.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return ""


__all__ = ["load_system_prompt"]
