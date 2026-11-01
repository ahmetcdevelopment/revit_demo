"""Starts the MCP server from any working directory (what Claude Code / Desktop launch).

The `brain` package lives in src/ and is not installed, so this launcher puts src/ on the path itself.
    uv run python tools/mcp_server.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from brain.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
