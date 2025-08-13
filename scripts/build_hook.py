"""Hatchling build hook to download Tenzir documentation before building."""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class DocsDownloadBuildHook(BuildHookInterface):
    """Build hook that downloads Tenzir docs before packaging."""

    PLUGIN_NAME = "docs-download"

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Download docs before building the package."""
        print("🔄 Downloading Tenzir documentation...", flush=True)

        # Path to the download script
        download_script = Path(self.root) / "scripts" / "download-docs.py"

        if not download_script.exists():
            print(f"⚠️  Warning: Download script not found at {download_script}", flush=True)
            print("⚠️  Skipping docs download", flush=True)
            return

        try:
            # Run the download script
            result = subprocess.run(
                ['uv', 'run', download_script],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            if result.returncode == 0:
                print("✅ Documentation downloaded successfully", flush=True)
                # Print any output from the script
                if result.stderr:
                    for line in result.stderr.strip().split('\n'):
                        if line.strip():
                            print(f"   {line}", flush=True)
            else:
                print(f"⚠️  Warning: Failed to download docs (exit code {result.returncode})", flush=True)
                if result.stderr:
                    print("   Error output:", flush=True)
                    for line in result.stderr.strip().split('\n'):
                        if line.strip():
                            print(f"   {line}", flush=True)
                print("⚠️  Continuing build without fresh docs", flush=True)

        except subprocess.TimeoutExpired:
            print("⚠️  Warning: Docs download timed out after 2 minutes", flush=True)
            print("⚠️  Continuing build without fresh docs", flush=True)
        except Exception as e:
            print(f"⚠️  Warning: Error downloading docs: {e}", flush=True)
            print("⚠️  Continuing build without fresh docs", flush=True)
