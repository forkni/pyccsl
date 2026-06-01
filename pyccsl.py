#!/usr/bin/env python3
"""
pyccsl - Python Claude Code Status Line
Generates a customizable status line for Claude Code showing performance metrics,
git status, session information, and cost calculations.

Exit Codes:
    0 - Success
    1 - Configuration/argument error
    2 - Input/JSON error
    3 - File access error (reserved)
    4 - Runtime/processing error (reserved)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any

__version__ = "0.9.40"

# Pricing data embedded from https://docs.anthropic.com/en/docs/about-claude/pricing
# All prices in USD per million tokens
PRICING_DATA = {
    "claude-opus-4-1-20250805": {
        "name": "Claude Opus 4.1",
        "input": 15.00,
        "cache_write_5m": 18.75,
        "cache_write_1h": 30.00,
        "cache_read": 1.50,
        "output": 75.00,
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4",
        "input": 15.00,
        "cache_write_5m": 18.75,
        "cache_write_1h": 30.00,
        "cache_read": 1.50,
        "output": 75.00,
    },
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4",
        "input": 3.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
        "output": 15.00,
    },
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "input": 3.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
        "output": 15.00,
    },
    "claude-3-7-sonnet-20250219": {
        "name": "Claude Sonnet 3.7",
        "input": 3.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
        "output": 15.00,
    },
    "claude-3-5-sonnet-20241022": {
        "name": "Claude Sonnet 3.5",
        "input": 3.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
        "output": 15.00,
    },
    "claude-3-5-sonnet-20240620": {
        "name": "Claude Sonnet 3.5",
        "input": 3.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
        "output": 15.00,
    },
    "claude-3-5-haiku-20241022": {
        "name": "Claude Haiku 3.5",
        "input": 0.80,
        "cache_write_5m": 1.00,
        "cache_write_1h": 1.60,
        "cache_read": 0.08,
        "output": 4.00,
    },
    "claude-3-haiku-20240307": {
        "name": "Claude Haiku 3",
        "input": 0.25,
        "cache_write_5m": 0.30,
        "cache_write_1h": 0.50,
        "cache_read": 0.03,
        "output": 1.25,
    },
}

# Theme definitions - 256-color ANSI codes
THEMES = {
    "default": {
        "folder": 208,  # Orange
        "git": 39,  # Blue
        "model": 141,  # Purple
        "input": 83,  # Green
        "output": 214,  # Gold
        "cost": 196,  # Red
    },
    "solarized": {
        "folder": 136,  # Yellow
        "git": 33,  # Blue
        "model": 61,  # Purple
        "input": 64,  # Green
        "output": 166,  # Orange
        "cost": 160,  # Red
    },
    "nord": {
        "folder": 223,  # Light beige
        "git": 109,  # Blue-green
        "model": 139,  # Purple
        "input": 108,  # Green
        "output": 179,  # Light orange
        "cost": 167,  # Nord red
    },
    "dracula": {
        "folder": 215,  # Orange
        "git": 117,  # Cyan
        "model": 141,  # Purple
        "input": 84,  # Green
        "output": 222,  # Yellow
        "cost": 203,  # Dracula red
    },
    "gruvbox": {
        "folder": 172,  # Orange
        "git": 66,  # Blue
        "model": 132,  # Purple
        "input": 106,  # Green
        "output": 214,  # Yellow
        "cost": 167,  # Gruvbox red
    },
    "tokyo": {
        "folder": 203,  # Pink
        "git": 75,  # Blue
        "model": 176,  # Purple
        "input": 115,  # Green
        "output": 221,  # Yellow
        "cost": 197,  # Tokyo red
    },
    "catppuccin": {
        "folder": 217,  # Peach
        "git": 117,  # Sky
        "model": 183,  # Mauve
        "input": 120,  # Green
        "output": 223,  # Yellow
        "cost": 210,  # Catppuccin red
    },
    "minimal": {
        "folder": 242,  # Gray
        "git": 245,  # Light gray
        "model": 248,  # Lighter gray
        "input": 250,  # Very light gray
        "output": 252,  # Almost white
        "cost": 252,  # Almost white (keep for minimal)
    },
    "none": {},  # No colors
}

# ANSI color code helpers
RESET = "\033[0m"
BOLD = "\033[1m"
GRAY_50 = "\033[38;5;244m"  # 50% gray for badge

# Powerline separator
POWERLINE_RIGHT = "\ue0b0"  # Powerline right arrow (requires powerline font)


def apply_color(
    text: str,
    fg_color: int | None = None,
    bg_color: int | None = None,
    bold: bool = False,
) -> str:
    """Apply ANSI color codes to text.

    Args:
        text: The text to colorize
        fg_color: Foreground color code (0-255) or None
        bg_color: Background color code (0-255) or None
        bold: Whether to make text bold

    Returns:
        Colored text with reset code at end
    """
    if not text:
        return text

    codes = []
    if bold:
        codes.append("1")
    if fg_color is not None:
        codes.append(f"38;5;{fg_color}")
    if bg_color is not None:
        codes.append(f"48;5;{bg_color}")

    if codes:
        return f"\033[{';'.join(codes)}m{text}{RESET}"
    return text


def get_field_color(field: str, theme_colors: dict[str, int]) -> int | None:
    """Get the color for a field based on the theme.

    Args:
        field: The field name
        theme_colors: Theme color dictionary

    Returns:
        Color code or None
    """
    if not theme_colors:  # none theme
        return None

    # Map fields to their color categories
    if field == "badge":
        return 244  # Always 50% gray for badge
    elif field == "folder":
        return theme_colors.get("folder")
    elif field == "git":
        return theme_colors.get("git")
    elif field in {
        "model",
        "weekly-limit",
        "perf-cache-rate",
        "perf-session-time",
        "perf-message-count",
        "perf-all-metrics",
    }:
        return theme_colors.get("model")
    elif field == "input":
        return theme_colors.get("input")
    elif field in {"output", "tokens", "compact-remaining"}:
        return theme_colors.get("output")
    elif field == "cost":
        return theme_colors.get("cost")
    elif field == "newline":
        return None
    return None


# Default field list
DEFAULT_FIELDS = ["badge", "folder", "git", "model", "tokens", "cost"]

# All available fields in display order.
# "newline" is a pseudo-field: when encountered it flushes the current line and
# starts a new one, allowing the status bar to span multiple terminal lines.
FIELD_ORDER = [
    "badge",
    "folder",
    "git",
    "model",
    "weekly-limit",
    "perf-cache-rate",
    "perf-session-time",
    "perf-message-count",
    "perf-all-metrics",
    "input",
    "output",
    "newline",
    "tokens",
    "compact-remaining",
    "cost",
]


def parse_env_file(filepath: str | None) -> dict[str, str]:
    """Parse environment file and return a dictionary of variables.

    File format:
    - Lines can be: VAR=value, VAR="value", or VAR='value'
    - Lines starting with # are comments
    - Empty lines are ignored
    - The file is also valid bash script syntax

    Returns dict of environment variable names to values.
    """
    env_vars = {}

    if not filepath or not os.path.exists(filepath):
        return env_vars

    try:
        with open(filepath, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse VAR=value format
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]

                    # Only process PYCCSL_ variables for security
                    if key.startswith("PYCCSL_"):
                        env_vars[key] = value

    except (OSError, UnicodeDecodeError) as e:
        # If there's an error reading the file, just continue without it
        sys.stderr.write(f"Warning: Could not read env file {filepath}: {e}\n")

    return env_vars


def parse_arguments() -> dict[str, Any]:
    """Parse command-line arguments and environment overrides.

    Reads CLI flags and optional env file, merges them (env file takes
    priority), parses threshold values, and resolves the field list.

    Returns:
        Dict with keys: theme, numbers, style, no_emoji, no_cost, debug,
        cache_thresholds (list[float]), fields (list[str]).

    Raises:
        SystemExit: With code 1 if threshold format is invalid.
    """
    # Debug: print raw sys.argv
    if "--debug" in sys.argv:
        sys.stderr.write(f"DEBUG: sys.argv = {sys.argv}\n")

    parser = argparse.ArgumentParser(
        description="Claude Code status line generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Theme option
    parser.add_argument(
        "--theme",
        choices=[
            "default",
            "solarized",
            "nord",
            "dracula",
            "gruvbox",
            "tokyo",
            "catppuccin",
            "minimal",
            "none",
        ],
        default=os.environ.get("PYCCSL_THEME", "default"),
        help="Color theme (default: default)",
    )

    # Number formatting option
    parser.add_argument(
        "--numbers",
        choices=["compact", "full", "raw"],
        default=os.environ.get("PYCCSL_NUMBERS", "compact"),
        help="Number formatting (default: compact)",
    )

    # Style option
    parser.add_argument(
        "--style",
        choices=["powerline", "simple", "arrows", "pipes", "dots"],
        default=os.environ.get("PYCCSL_STYLE", "simple"),
        help="Separator style (default: simple)",
    )

    # No emoji option
    parser.add_argument(
        "--no-emoji",
        action="store_true",
        default=os.environ.get("PYCCSL_NO_EMOJI", "false").lower() == "true",
        help="Disable emoji in output",
    )

    # No cost option
    parser.add_argument(
        "--no-cost",
        action="store_true",
        default=os.environ.get("PYCCSL_NO_COST", "false").lower() == "true",
        help="Disable cost calculation and display (for Max subscription users)",
    )

    # Debug option
    parser.add_argument(
        "--debug", action="store_true", help="Output debug information to stderr"
    )

    # Environment file option
    parser.add_argument(
        "--env", help="Path to environment file with PYCCSL_* variables"
    )

    # Performance thresholds - cache
    parser.add_argument(
        "--perf-cache",
        default=os.environ.get("PYCCSL_PERF_CACHE", "95,90,75"),
        help="Cache hit rate thresholds (green,yellow,orange) (default: 95,90,75)",
    )

    # Absolute manual override for the auto-compact threshold.  When > 0 this value
    # is used directly, bypassing the formula; 0 (default) means derive from the
    # effective window and percentage instead of using a hardcoded token count.
    parser.add_argument(
        "--compact-threshold",
        type=int,
        default=int(os.environ.get("PYCCSL_COMPACT_THRESHOLD", "0")),
        help="Absolute token threshold override (default: 0 = derive from formula). "
        "When > 0, overrides all other compact-threshold settings.",
    )

    # Context window size (combined with --compact-pct to derive the threshold)
    parser.add_argument(
        "--context-window",
        type=int,
        default=int(os.environ.get("PYCCSL_CONTEXT_WINDOW", "200000")),
        help="Model context window in tokens (default: 200000; use 1000000 for 1M-context models)",
    )

    # Auto-compact percentage - kept in sync with Claude Code's global
    # CLAUDE_AUTOCOMPACT_PCT_OVERRIDE setting.  Mirrors Claude Code's Math.min
    # clamp: the value can only lower the trigger below the default (window−buffer),
    # never raise it above it.  0 = unset → use the default path (window−buffer).
    parser.add_argument(
        "--compact-pct",
        type=float,
        default=float(
            os.environ.get(
                "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
                os.environ.get("PYCCSL_COMPACT_PCT", "0"),
            )
            or "0"
        ),
        help="Auto-compact trigger as %% of the effective window. Defaults to "
        "$CLAUDE_AUTOCOMPACT_PCT_OVERRIDE so the counter stays in sync with global settings.",
    )

    # Effective window for compaction math - mirrors CLAUDE_CODE_AUTO_COMPACT_WINDOW.
    # 0 = unset → fall back to --context-window (the model's real window).
    # Capped at --context-window in the threshold formula so it can only shrink.
    parser.add_argument(
        "--auto-compact-window",
        type=int,
        default=int(
            os.environ.get(
                "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
                os.environ.get("PYCCSL_AUTO_COMPACT_WINDOW", "0"),
            )
            or "0"
        ),
        help="Effective context window in tokens for compact math "
        "(default: 0 = use --context-window). Mirrors $CLAUDE_CODE_AUTO_COMPACT_WINDOW.",
    )

    # Reserved response buffer subtracted on the unset-pct (default threshold) path.
    # Claude Code reserves ~13 000 tokens for response generation.
    parser.add_argument(
        "--compact-buffer",
        type=int,
        default=int(os.environ.get("PYCCSL_COMPACT_BUFFER", "13000")),
        help="Token buffer reserved for responses, subtracted from effective window "
        "when computing the default (no-pct) threshold (default: 13000).",
    )

    # Fields to display (positional argument)
    parser.add_argument(
        "fields",
        nargs="?",
        default=os.environ.get("PYCCSL_FIELDS", None),
        help="Comma-separated list of fields to display",
    )

    args = parser.parse_args()

    # Load environment file if specified
    env_vars = {}
    if args.env:
        env_vars = parse_env_file(args.env)
        if args.debug and env_vars:
            sys.stderr.write(
                f"DEBUG: Loaded env vars from {args.env}: {list(env_vars.keys())}\n"
            )

    # Apply env file overrides (higher priority than command line)
    # This allows dynamic configuration changes by modifying the env file
    if "PYCCSL_THEME" in env_vars:
        args.theme = env_vars["PYCCSL_THEME"]
    if "PYCCSL_NUMBERS" in env_vars:
        args.numbers = env_vars["PYCCSL_NUMBERS"]
    if "PYCCSL_STYLE" in env_vars:
        args.style = env_vars["PYCCSL_STYLE"]
    if "PYCCSL_NO_EMOJI" in env_vars:
        args.no_emoji = env_vars["PYCCSL_NO_EMOJI"].lower() == "true"
    if "PYCCSL_NO_COST" in env_vars:
        args.no_cost = env_vars["PYCCSL_NO_COST"].lower() == "true"
    if "PYCCSL_PERF_CACHE" in env_vars:
        args.perf_cache = env_vars["PYCCSL_PERF_CACHE"]
    if "PYCCSL_COMPACT_THRESHOLD" in env_vars:
        try:
            args.compact_threshold = int(env_vars["PYCCSL_COMPACT_THRESHOLD"])
        except ValueError:
            pass
    if "PYCCSL_CONTEXT_WINDOW" in env_vars:
        try:
            args.context_window = int(env_vars["PYCCSL_CONTEXT_WINDOW"])
        except ValueError:
            pass
    if "PYCCSL_COMPACT_PCT" in env_vars:
        try:
            args.compact_pct = float(env_vars["PYCCSL_COMPACT_PCT"])
        except ValueError:
            pass
    if "PYCCSL_AUTO_COMPACT_WINDOW" in env_vars:
        try:
            args.auto_compact_window = int(env_vars["PYCCSL_AUTO_COMPACT_WINDOW"])
        except ValueError:
            pass
    if "PYCCSL_COMPACT_BUFFER" in env_vars:
        try:
            args.compact_buffer = int(env_vars["PYCCSL_COMPACT_BUFFER"])
        except ValueError:
            pass
    if "PYCCSL_FIELDS" in env_vars:
        args.fields = env_vars["PYCCSL_FIELDS"]

    # Parse fields
    if args.fields:
        # Split comma-separated fields and strip whitespace
        fields = [f.strip() for f in args.fields.split(",") if f.strip()]
        # If all fields were empty/whitespace, use defaults
        if not fields:
            if "--debug" in sys.argv:
                sys.stderr.write("DEBUG: Empty fields specified, using defaults\n")
            fields = DEFAULT_FIELDS.copy()
    else:
        if "--debug" in sys.argv:
            sys.stderr.write("DEBUG: No fields specified, using defaults\n")
        fields = DEFAULT_FIELDS.copy()

    # Parse threshold values
    try:
        cache_thresholds = [float(x) for x in args.perf_cache.split(",")]
        if len(cache_thresholds) != 3:
            raise ValueError("Need exactly 3 cache thresholds")
    except (ValueError, AttributeError):
        print(
            "Error: Invalid cache thresholds format. Expected: three comma-separated numbers (e.g., 95,90,75)",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "theme": args.theme,
        "numbers": args.numbers,
        "style": args.style,
        "no_emoji": args.no_emoji,
        "no_cost": args.no_cost,
        "debug": args.debug,
        "cache_thresholds": cache_thresholds,
        "compact_threshold": args.compact_threshold,
        "context_window": args.context_window,
        "compact_pct": args.compact_pct,
        "auto_compact_window": args.auto_compact_window,
        "compact_buffer": args.compact_buffer,
        "fields": fields,
    }


def read_input() -> dict[str, Any]:
    """Read and parse JSON input from stdin.

    Returns:
        Parsed JSON data as a dictionary.

    Raises:
        SystemExit: With code 2 if stdin is a terminal, input is empty,
            or JSON is invalid.
    """
    try:
        # Check if stdin has data (not a terminal)
        if sys.stdin.isatty():
            print(
                "Error: No input provided. This script expects JSON data via stdin from Claude Code.",
                file=sys.stderr,
            )
            sys.exit(2)

        # Read from stdin
        input_data = sys.stdin.read()

        if not input_data.strip():
            print("Error: Empty input received.", file=sys.stderr)
            sys.exit(2)

        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            sys.exit(2)

        return data

    except OSError as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(2)


def extract_model_info(data: dict[str, Any]) -> dict[str, Any]:
    """Extract model information from input data.

    Supports both legacy and 2.0.1 input formats.

    Returns:
        Dict with display_name, id, and optional cost info
    """
    try:
        model_info = {"display_name": "Unknown", "id": None}

        # Extract model information
        if "model" in data:
            model = data["model"]
            if isinstance(model, dict):
                model_info["display_name"] = model.get("display_name", "Unknown")
                model_info["id"] = model.get("id", None)

                # 2.0.1: Extract cost info if present
                if "info" in model and isinstance(model["info"], dict):
                    model_info["session_cost"] = model["info"].get("session_cost")
                    model_info["daily_usage_percent"] = model["info"].get(
                        "daily_usage_percent"
                    )
            elif isinstance(model, str):
                # Handle string model ID (legacy format)
                model_info["id"] = model
                # Try to get display name from pricing data
                if model in PRICING_DATA:
                    model_info["display_name"] = PRICING_DATA[model]["name"]

        return model_info
    except (KeyError, TypeError, AttributeError):
        return {"display_name": "Unknown", "id": None}


def extract_workspace_info(input_data: dict[str, Any]) -> dict[str, Any]:
    """Extract workspace information from input data.

    Supports 2.0.1 workspace fields with fallback to legacy cwd.

    Returns:
        Dict with current_dir, project_dir, and working_dir
    """
    workspace_info = {}

    # 2.0.1: Check for workspace fields first
    if "workspace" in input_data and isinstance(input_data["workspace"], dict):
        workspace = input_data["workspace"]
        workspace_info["current_dir"] = workspace.get("current_dir")
        workspace_info["project_dir"] = workspace.get("project_dir")
        # Use current_dir as the working directory
        workspace_info["working_dir"] = workspace.get("current_dir", os.getcwd())
    else:
        # Legacy: Use cwd field
        cwd = input_data.get("cwd", os.getcwd())
        workspace_info["working_dir"] = cwd
        workspace_info["current_dir"] = cwd
        workspace_info["project_dir"] = None

    return workspace_info


def extract_git_status(input_data: dict[str, Any]) -> dict[str, Any]:
    """Extract git status information from the current directory.

    Returns a dict with:
    - branch: Current branch name or None
    - modified_count: Number of modified/staged files or 0
    """
    try:
        # Get working directory from workspace or cwd
        workspace_info = extract_workspace_info(input_data)
        cwd = workspace_info["working_dir"]

        # Get current branch name
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if branch_result.returncode != 0:
            # Not a git repository
            return {"branch": None, "modified_count": 0}

        branch = branch_result.stdout.strip()

        # Get modified file count using porcelain format
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )

        # Count non-empty lines (each represents a modified file)
        modified_count = 0
        if status_result.returncode == 0:
            modified_count = len(
                [line for line in status_result.stdout.splitlines() if line.strip()]
            )

        return {"branch": branch, "modified_count": modified_count}

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Git not available or timeout
        return {"branch": None, "modified_count": 0}
    except (OSError, ValueError):
        # Any other error - fail silently
        return {"branch": None, "modified_count": 0}


def get_model_pricing(model_id: str | None) -> dict[str, Any] | None:
    """Get pricing information for a model ID.

    Returns a dict with pricing info or None if model not found.
    """
    if model_id and model_id in PRICING_DATA:
        return PRICING_DATA[model_id]
    return None


def load_transcript(
    transcript_path: str | None, debug: bool = False
) -> list[dict[str, Any]]:
    """Load and parse a Claude Code transcript JSONL file.

    Args:
        transcript_path: Path to the transcript file
        debug: Whether to output debug information

    Returns:
        List of parsed JSON entries, or empty list on error
    """
    if not transcript_path:
        if debug:
            sys.stderr.write("DEBUG: No transcript path provided\n")
        return []

    if not os.path.exists(transcript_path):
        if debug:
            sys.stderr.write(
                f"DEBUG: Transcript file does not exist: {transcript_path}\n"
            )
        return []

    try:
        entries = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue  # Skip empty lines
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    # Log error but continue processing other lines
                    print(
                        f"Warning: Invalid JSON at line {line_num} in transcript: {e}",
                        file=sys.stderr,
                    )
                    continue
        if debug:
            sys.stderr.write(
                f"DEBUG: Successfully loaded {len(entries)} transcript entries\n"
            )
        return entries
    except FileNotFoundError:
        # Transcript file not found - this is expected for new sessions
        if debug:
            sys.stderr.write(f"DEBUG: Transcript file not found: {transcript_path}\n")
        return []
    except (PermissionError, IOError) as e:
        # File access errors
        if debug:
            sys.stderr.write(f"DEBUG: Cannot access transcript file: {e}\n")
        return []
    except (OSError, UnicodeDecodeError) as e:
        # Other unexpected errors
        if debug:
            sys.stderr.write(f"DEBUG: Unexpected error reading transcript: {e}\n")
        return []


def calculate_token_usage(
    transcript_entries: list[dict[str, Any]],
) -> dict[str, int]:
    """Calculate total token usage from transcript entries.

    Args:
        transcript_entries: List of parsed transcript entries

    Returns:
        Dict with token totals: input_tokens, output_tokens,
        cache_creation_tokens, cache_read_tokens
    """
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
    }

    for entry in transcript_entries:
        usage = None

        # Check for usage in assistant messages
        if entry.get("type") == "assistant" and "message" in entry:
            usage = entry["message"].get("usage", {})

        # Check for usage in tool use results (only if it's a dict)
        elif "toolUseResult" in entry and isinstance(entry["toolUseResult"], dict):
            usage = entry["toolUseResult"].get("usage", {})

        if usage:
            # Add tokens to totals
            totals["input_tokens"] += usage.get("input_tokens", 0)
            totals["output_tokens"] += usage.get("output_tokens", 0)
            totals["cache_creation_tokens"] += usage.get(
                "cache_creation_input_tokens", 0
            )
            totals["cache_read_tokens"] += usage.get("cache_read_input_tokens", 0)

    return totals


def get_current_context_size(
    transcript_entries: list[dict[str, Any]],
) -> int:
    """Return the live context-window size from the most recent assistant entry.

    Unlike calculate_token_usage which sums across the session, this returns
    just the last assistant message's input-side tokens (base + cache_read +
    cache_creation), which is what Claude Code checks against its auto-compact
    threshold.
    """
    for entry in reversed(transcript_entries):
        if entry.get("type") == "assistant" and "message" in entry:
            usage = entry["message"].get("usage", {})
            if usage:
                return (
                    usage.get("input_tokens", 0)
                    + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0)
                )
    return 0


def get_model_from_transcript(
    transcript_entries: list[dict[str, Any]],
) -> str | None:
    """Extract the model ID from transcript entries.

    Looks for the first assistant message with a model ID.

    Args:
        transcript_entries: List of parsed transcript entries

    Returns:
        Model ID string or None if not found
    """
    for entry in transcript_entries:
        if entry.get("type") == "assistant" and "message" in entry:
            model_id = entry["message"].get("model")
            if model_id:
                return model_id
    return None


def calculate_cost_per_entry(usage: dict[str, int], model_id: str) -> float:
    """Calculate cost for a single entry based on its token usage and model.

    Args:
        usage: Dict with token usage for this entry
        model_id: Model ID string for pricing lookup

    Returns:
        Cost in dollars (float) or 0.0 if model not found
    """
    pricing = get_model_pricing(model_id)
    if not pricing:
        return 0.0

    # Calculate cost using the formula (all rates are per million tokens)
    # Using 5-minute cache write rate (Claude Code default)
    cost = (
        usage.get("input_tokens", 0) * pricing.get("input", 0)
        + usage.get("cache_creation_input_tokens", 0) * pricing.get("cache_write_5m", 0)
        + usage.get("cache_read_input_tokens", 0) * pricing.get("cache_read", 0)
        + usage.get("output_tokens", 0) * pricing.get("output", 0)
    ) / 1_000_000

    return cost


def calculate_total_cost(
    transcript_entries: list[dict[str, Any]], debug: bool = False
) -> float:
    """Calculate total session cost by summing per-entry costs using each entry's model.

    Args:
        transcript_entries: List of parsed transcript entries
        debug: Whether to output debug information

    Returns:
        Total cost in dollars (float)
    """
    total_cost = 0.0
    model_costs = {}  # Track costs per model for debugging

    # Build UUID lookup for finding parent models
    uuid_lookup = {}
    for entry in transcript_entries:
        uuid = entry.get("uuid")
        if uuid:
            uuid_lookup[uuid] = entry

    # Track the last seen model for tool results that don't specify one
    last_model_id = None

    for entry in transcript_entries:
        usage = None
        model_id = None

        # Check for usage and model in assistant messages
        if entry.get("type") == "assistant" and "message" in entry:
            message = entry["message"]
            usage = message.get("usage", {})
            model_info = message.get("model")

            # Handle both string and dict formats for model
            if isinstance(model_info, dict):
                model_id = model_info.get("id")
            else:
                model_id = model_info

            if model_id:
                last_model_id = model_id  # Remember this model

        # Check for usage in tool use results
        elif "toolUseResult" in entry and isinstance(entry["toolUseResult"], dict):
            usage = entry["toolUseResult"].get("usage", {})

            # Try to find model from parent assistant message
            parent_uuid = entry.get("parentUuid")
            if parent_uuid and parent_uuid in uuid_lookup:
                parent = uuid_lookup[parent_uuid]
                if parent.get("type") == "assistant" and "message" in parent:
                    parent_model = parent["message"].get("model")
                    # Extract model ID from dict if needed
                    if isinstance(parent_model, dict):
                        model_id = parent_model.get("id")
                    else:
                        model_id = parent_model

            # Fallback to last seen model if parent lookup fails
            if not model_id:
                model_id = last_model_id

        if usage and model_id:
            entry_cost = calculate_cost_per_entry(usage, model_id)
            total_cost += entry_cost

            # Track per-model costs for debugging
            if model_id not in model_costs:
                model_costs[model_id] = 0.0
            model_costs[model_id] += entry_cost
        elif usage and not model_id and debug:
            # Log entries with usage but no model
            sys.stderr.write(
                f"DEBUG: Entry with usage but no model: {entry.get('uuid', 'unknown')[:8]}\n"
            )

    if debug and model_costs:
        sys.stderr.write("DEBUG: Cost breakdown by model:\n")
        for model_id, cost in model_costs.items():
            sys.stderr.write(f"DEBUG:   {model_id}: ${cost:.4f}\n")
        sys.stderr.write(f"DEBUG:   Total: ${total_cost:.4f}\n")

    return total_cost


def format_cost(cost: float) -> str:
    """Format cost as dollars or cents.

    Args:
        cost: Cost in dollars (float)

    Returns:
        Formatted string (e.g., "$1.25" or "48¢")
    """
    if cost >= 1.0:
        return f"${cost:.2f}"
    else:
        cents = int(round(cost * 100))
        return f"{cents}¢"


def format_number(value: int | float, style: str = "compact") -> str:
    """Format a number based on style preference.

    Args:
        value: Number to format.
        style: Formatting mode — "compact" (e.g., "1.2K", "3M"), "full"
            (e.g., "1,234"), or "raw" (e.g., "1234").

    Returns:
        Human-readable string representation of the number.
    """
    if style == "compact":
        if value >= 1_000_000:
            # Remove .0 for whole millions
            formatted = value / 1_000_000
            if formatted == int(formatted):
                return f"{int(formatted)}M"
            return f"{formatted:.1f}M"
        elif value >= 1_000:
            # Remove .0 for whole thousands
            formatted = value / 1_000
            if formatted == int(formatted):
                return f"{int(formatted)}K"
            return f"{formatted:.1f}K"
        else:
            return str(value)
    elif style == "full":
        return f"{value:,}"
    else:  # raw
        return str(value)


def calculate_performance_badge(
    cache_hit_rate: float,
    cache_thresholds: list[float],
    colored: bool = False,
    powerline: bool = False,
    no_emoji: bool = False,
) -> str:
    """Calculate performance badge based on cache hit rate.

    Args:
        cache_hit_rate: Cache hit rate (0.0 to 1.0)
        cache_thresholds: List of [green, yellow, orange] thresholds for cache hit rate
        colored: Whether to apply colors to the badge
        powerline: Whether this is for powerline style (different coloring)
        no_emoji: Whether to use text characters instead of emoji

    Returns:
        Badge string (e.g., "●○○○", "○●○○", "○○●○", "○○○●")
    """
    # Calculate performance level for cache hit rate (higher is better)
    cache_percent = cache_hit_rate * 100
    if cache_percent >= cache_thresholds[0]:
        overall_level = 0  # Green
    elif cache_percent >= cache_thresholds[1]:
        overall_level = 1  # Yellow
    elif cache_percent >= cache_thresholds[2]:
        overall_level = 2  # Orange
    else:
        overall_level = 3  # Red

    # Choose characters based on emoji preference and color availability
    active_char = "*" if no_emoji else "●"
    # When no colors, use open circles for inactive so they're distinguishable
    # When colors are used, use filled circles for both (distinguished by color)
    inactive_char = "o" if no_emoji else ("○" if not colored else "●")

    # Generate badge string with colors if requested
    if colored:
        # Define colors for each level: green, darker yellow, orange, red
        colors = [82, 220, 208, 196]  # ANSI 256-color codes (220 is darker yellow)

        if powerline:
            # Powerline style: gray background throughout, black dots except for the active one
            # Build the entire string with continuous gray background
            result = "\033[48;5;244m"  # Start with 50% gray background
            for i in range(4):
                if i == overall_level:
                    # Active dot - just change foreground color, keep gray background
                    result += f"\033[38;5;{colors[i]}m{active_char}"
                else:
                    # Inactive dot - black foreground, keep gray background
                    result += f"\033[38;5;0m{inactive_char}"
            # Don't add RESET here - let the powerline handler manage that
            return result
        else:
            # Regular style: colored active dot, gray inactive dots
            gray = 244  # Gray for inactive dots
            dots = []
            for i in range(4):
                if i == overall_level:
                    # Active dot with its color
                    dots.append(apply_color(active_char, fg_color=colors[i]))
                else:
                    # Inactive dot - gray outline
                    dots.append(apply_color(inactive_char, fg_color=gray))
            return "".join(dots)
    else:
        # Plain badge without colors
        badges = [
            f"{active_char}{inactive_char}{inactive_char}{inactive_char}",
            f"{inactive_char}{active_char}{inactive_char}{inactive_char}",
            f"{inactive_char}{inactive_char}{active_char}{inactive_char}",
            f"{inactive_char}{inactive_char}{inactive_char}{active_char}",
        ]
        return badges[overall_level]


def calculate_performance_metrics(
    transcript_entries: list[dict[str, Any]],
    token_totals: dict[str, int],
    debug: bool = False,
) -> dict[str, Any]:
    """Calculate performance metrics from transcript.

    Args:
        transcript_entries: List of parsed transcript entries
        token_totals: Dict with token usage totals
        debug: Whether to output debug information

    Returns:
        Dict with performance metrics
    """
    metrics = {}

    # Calculate cache hit rate
    total_input = (
        token_totals.get("input_tokens", 0)
        + token_totals.get("cache_creation_tokens", 0)
        + token_totals.get("cache_read_tokens", 0)
    )
    if total_input > 0:
        cache_hit_rate = token_totals.get("cache_read_tokens", 0) / total_input
        metrics["cache_hit_rate"] = cache_hit_rate
    else:
        metrics["cache_hit_rate"] = 0.0

    # Count messages and calculate session duration
    user_timestamps = []
    all_timestamps = []

    # Process entries to collect timestamps
    for entry in transcript_entries:
        timestamp_str = entry.get("timestamp")
        if not timestamp_str:
            continue

        try:
            # Parse ISO format timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        all_timestamps.append(timestamp)

        entry_type = entry.get("type")

        # Track user timestamps for message count
        if entry_type == "user":
            user_timestamps.append(timestamp)

    # Message count
    metrics["message_count"] = len(user_timestamps)

    # Session duration
    if len(all_timestamps) >= 2:
        all_timestamps.sort()
        session_duration = (all_timestamps[-1] - all_timestamps[0]).total_seconds()
        metrics["session_duration"] = session_duration
    else:
        metrics["session_duration"] = 0.0

    return metrics


def get_weekly_limit_for_model(
    model_id: str, debug: bool = False
) -> dict[str, int] | None:
    """Get weekly message limit for the specified model from manual config.

    Since Claude Code doesn't expose weekly limits via API, this reads from
    a manual configuration file: ~/.claude/weekly_limits.json

    Expected format:
    {
        "claude-sonnet-4-5-20250929": {"current": 1234, "limit": 5000},
        "claude-opus-4-1-20250805": {"current": 45, "limit": 500}
    }

    Args:
        model_id: Model ID string (e.g., "claude-sonnet-4-5-20250929")
        debug: Whether to output debug information

    Returns:
        Dict with "current" and "limit" message counts, or None if unavailable
    """
    try:
        # Path to manual limits config file
        limits_file = os.path.expanduser("~/.claude/weekly_limits.json")

        if not os.path.exists(limits_file):
            if debug:
                sys.stderr.write(
                    f"DEBUG: No weekly_limits.json found at {limits_file}\n"
                )
                sys.stderr.write(
                    'DEBUG: Create this file manually with format: {"model-id": {"current": N, "limit": M}}\n'
                )
            return None

        # Read and parse the limits file
        with open(limits_file, "r", encoding="utf-8") as f:
            limits_data = json.load(f)

        # Look up this model's limits
        if model_id in limits_data:
            limit_info = limits_data[model_id]
            if (
                isinstance(limit_info, dict)
                and "current" in limit_info
                and "limit" in limit_info
            ):
                if debug:
                    sys.stderr.write(
                        f"DEBUG: Found weekly limit for {model_id}: {limit_info}\n"
                    )
                return limit_info

        if debug:
            sys.stderr.write(f"DEBUG: No limit entry found for model {model_id}\n")
        return None

    except json.JSONDecodeError as e:
        if debug:
            sys.stderr.write(f"DEBUG: Invalid JSON in weekly_limits.json: {e}\n")
        return None
    except (OSError, TypeError, KeyError) as e:
        if debug:
            sys.stderr.write(f"DEBUG: Error reading weekly limits: {e}\n")
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds (non-negative float).

    Returns:
        Compact string such as "45.0s", "12m", "3.5h", or "2d".
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.0f}m"
    else:
        hours = seconds / 3600
        if hours < 24:
            return f"{hours:.1f}h"
        else:
            days = hours / 24
            return f"{days:.0f}d"


def format_output(
    config: dict[str, Any],
    model_info: dict[str, Any],
    input_data: dict[str, Any],
    metrics: dict[str, Any] | None = None,
) -> str:
    """Format the output based on selected fields and configuration.

    Args:
        config: Configuration dict from parse_arguments()
        model_info: Model information dict with display_name and id
        input_data: Full input JSON data
        metrics: Dict with calculated metrics (cost, tokens, etc.)

    Returns:
        Formatted string for output
    """
    if metrics is None:
        metrics = {}

    debug = config.get("debug", False)

    if debug:
        sys.stderr.write("DEBUG: === format_output ===\n")
        sys.stderr.write(f"DEBUG: Requested fields: {config['fields']}\n")
        sys.stderr.write(f"DEBUG: Available metrics: {list(metrics.keys())}\n")
        if not metrics:
            sys.stderr.write("DEBUG: WARNING: metrics dict is empty!\n")
        sys.stderr.write(f"DEBUG: Model info: {model_info}\n")

    # Get theme colors
    theme_colors = THEMES.get(config["theme"], {})
    is_powerline = config["style"] == "powerline"

    # Storage: list-of-lines, each line is a list of parts (non-powerline) or
    # a list of (text, bg_color) tuples (powerline).  A "newline" pseudo-field
    # appends a fresh inner list so subsequent fields land on the next line.
    output_lines = [[]]   # list[list[str]]   — non-powerline / no-theme powerline
    segment_lines = [[]]  # list[list[tuple]] — powerline with theme

    # Get separator based on style (for non-powerline)
    if config["style"] == "pipes":
        separator = " | "
    elif config["style"] == "arrows":
        separator = " → "
    elif config["style"] == "dots":
        separator = " · "
    else:  # simple or powerline fallback
        separator = " > "

    # Process fields in FIELD_ORDER sequence
    for field in FIELD_ORDER:
        if field not in config["fields"]:
            continue

        if debug:
            sys.stderr.write(f"DEBUG: Processing field: {field}\n")

        # "newline" pseudo-field: start a new output line
        if field == "newline":
            output_lines.append([])
            segment_lines.append([])
            if debug:
                sys.stderr.write("DEBUG: newline field — starting next line\n")
            continue

        # Prepare field content
        field_content = None

        # Handle different fields
        if field == "badge":
            if "badge" in metrics:
                field_content = metrics["badge"]
            else:
                # Show default badge when no performance data is available
                active_char = "*" if config["no_emoji"] else "●"
                inactive_char = "o" if config["no_emoji"] else "○"
                # Default badge: all inactive (no performance data yet)
                default_badge = (
                    f"{inactive_char}{inactive_char}{inactive_char}{inactive_char}"
                )

                # Apply colors if theme is not "none"
                if config["theme"] != "none":
                    is_powerline = config["style"] == "powerline"
                    if is_powerline:
                        # Powerline style with gray background
                        field_content = f"\033[48;5;244m\033[38;5;0m{default_badge}"
                    else:
                        # Regular style with gray foreground
                        field_content = apply_color(default_badge, fg_color=244)
                else:
                    field_content = default_badge

                if debug:
                    sys.stderr.write(
                        f"DEBUG: Badge not in metrics - showing default: {default_badge}\n"
                    )
        elif field == "model":
            if "display_name" in model_info:
                field_content = model_info["display_name"]
            elif debug:
                sys.stderr.write(
                    f"DEBUG: No display_name in model_info: {model_info}\n"
                )
        elif field == "weekly-limit" and "weekly_limit" in metrics:
            # Format weekly limit: "1.2K/5K msgs"
            current = metrics["weekly_limit"]["current"]
            limit = metrics["weekly_limit"]["limit"]
            current_str = format_number(current, config["numbers"])
            limit_str = format_number(limit, config["numbers"])
            if config["no_emoji"]:
                field_content = f"Msgs: {current_str}/{limit_str}"
            else:
                field_content = f"📊 {current_str}/{limit_str}"
        elif field == "folder":
            # Extract folder name from workspace or cwd
            workspace_info = extract_workspace_info(input_data)
            cwd = workspace_info["working_dir"]
            drive, tail = os.path.splitdrive(cwd)
            folder_name = os.path.basename(cwd)
            # Handle root directory
            if not folder_name:
                folder_name = (
                    "/" if cwd == "/" else os.path.basename(os.path.dirname(cwd))
                )
            # Truncate if too long
            if len(folder_name) > 20:
                folder_name = folder_name[:17] + "..."
            # Prepend drive letter on Windows (e.g. "C: myproject") so mirrored
            # projects on different drives are distinguishable at a glance.
            if drive:
                field_content = f"{drive}\\{folder_name}"
            else:
                field_content = folder_name
        elif field == "input" and any(
            k in metrics
            for k in ["input_tokens", "cache_creation_tokens", "cache_read_tokens"]
        ):
            # Display as tuple: (base, cache_write, cache_read)
            base = format_number(metrics.get("input_tokens", 0), config["numbers"])
            cache_write = format_number(
                metrics.get("cache_creation_tokens", 0), config["numbers"]
            )
            cache_read = format_number(
                metrics.get("cache_read_tokens", 0), config["numbers"]
            )
            prefix = "In:" if config["no_emoji"] else "↑"
            field_content = f"{prefix} ({base}, {cache_write}, {cache_read})"
        elif field == "output" and "output_tokens" in metrics:
            prefix = "Out:" if config["no_emoji"] else "↓"
            field_content = (
                f"{prefix} {format_number(metrics['output_tokens'], config['numbers'])}"
            )
        elif field == "tokens" and "current_context_size" in metrics:
            # Show live context (last turn's input+cache tokens) — same basis Claude Code
            # uses for its compact-remaining % and context_window.used_percentage.
            prefix = "Tok:" if config["no_emoji"] else "◊"
            field_content = (
                f"{prefix} {format_number(metrics['current_context_size'], config['numbers'])}"
            )
        elif field == "compact-remaining" and "compact_remaining" in metrics:
            remaining = metrics["compact_remaining"]
            prefix = "Cmpct:" if config["no_emoji"] else "⏳"
            field_content = f"{prefix} {format_number(remaining, config['numbers'])}"
        elif field == "cost":
            if "cost_formatted" in metrics:
                field_content = metrics["cost_formatted"]
            else:
                # Show $0.00 when no cost data is available
                field_content = "$0.00"
                if debug:
                    sys.stderr.write(
                        "DEBUG: Cost not available - showing default $0.00\n"
                    )
        elif field == "git" and "git_info" in metrics:
            # Format git status: "branch ●" if modified, "branch" if clean
            branch = metrics["git_info"]["branch"]
            modified = metrics["git_info"]["modified_count"]
            if modified > 0:
                indicator = "*" if config["no_emoji"] else "●"
                field_content = f"{branch} {indicator}"
            else:
                field_content = branch
        elif field == "perf-cache-rate" and "cache_hit_rate" in metrics:
            # Format cache hit rate as percentage
            rate = metrics["cache_hit_rate"] * 100
            if config["no_emoji"]:
                field_content = f"Cache: {rate:.0f}%"
            else:
                field_content = f"⚡ {rate:.0f}%"
        elif field == "perf-session-time" and "session_duration" in metrics:
            # Format session duration
            time_str = format_duration(metrics["session_duration"])
            if config["no_emoji"]:
                field_content = f"Session: {time_str}"
            else:
                field_content = f"🕐 {time_str}"
        elif field == "perf-message-count" and "message_count" in metrics:
            # Format message count
            count = metrics["message_count"]
            if config["no_emoji"]:
                field_content = f"Messages: {count}"
            else:
                field_content = f"💬 {count}"
        elif field == "perf-all-metrics":
            # Show all performance metrics together
            # Use different separator based on emoji setting
            sep = "●" if not config["no_emoji"] else "|"

            perf_parts = []
            if "cache_hit_rate" in metrics:
                rate = metrics["cache_hit_rate"] * 100
                perf_parts.append(
                    f"⚡ {rate:.0f}% {sep}"
                    if not config["no_emoji"]
                    else f"Cache: {rate:.0f}% {sep}"
                )
            else:
                # Default: 0% cache hit rate
                perf_parts.append(
                    f"⚡ 0% {sep}" if not config["no_emoji"] else f"Cache: 0% {sep}"
                )

            if "session_duration" in metrics:
                time_str = format_duration(metrics["session_duration"])
                perf_parts.append(
                    f"🕐 {time_str} {sep}"
                    if not config["no_emoji"]
                    else f"Session: {time_str} {sep}"
                )
            else:
                # Default: 0s session duration
                perf_parts.append(
                    f"🕐 0s {sep}" if not config["no_emoji"] else f"Session: 0s {sep}"
                )

            if "message_count" in metrics:
                count = metrics["message_count"]
                perf_parts.append(
                    f"💬 {count}" if not config["no_emoji"] else f"Messages: {count}"
                )
            else:
                # Default: 0 messages
                perf_parts.append("💬 0" if not config["no_emoji"] else "Messages: 0")

            field_content = " ".join(perf_parts)

        # Add field to output
        if field_content:
            if debug:
                sys.stderr.write(
                    f"DEBUG: Adding field '{field}' with content: '{field_content[:50]}...'\n"
                )

            if is_powerline and config["theme"] != "none":
                # For powerline, store segment with its background color
                bg_color = get_field_color(field, theme_colors)
                if field == "badge":
                    # Badge gets 50% gray background in powerline mode for better contrast
                    bg_color = 244  # 50% gray
                segment_lines[-1].append((field_content, bg_color))
            else:
                # Regular styling - apply foreground color
                if field != "badge":
                    color = get_field_color(field, theme_colors)
                    if color is not None:
                        field_content = apply_color(field_content, fg_color=color)
                output_lines[-1].append(field_content)
        else:
            if debug:
                sys.stderr.write(f"DEBUG: Field '{field}' has no content, skipping\n")

    def _build_powerline_line(segments: list[tuple]) -> str:
        """Render one line's worth of powerline segments."""
        grouped: list[tuple[str, int | None]] = []
        cur_group: list[str] = []
        cur_bg = None
        for text, bg_color in segments:
            if bg_color == cur_bg and cur_bg is not None:
                cur_group.append(text)
            else:
                if cur_group:
                    grouped.append((" ".join(cur_group), cur_bg))
                cur_group = [text]
                cur_bg = bg_color
        if cur_group:
            grouped.append((" ".join(cur_group), cur_bg))

        result: list[str] = []
        for i, (text, bg_color) in enumerate(grouped):
            if bg_color is None:
                continue
            result.append(apply_color(f" {text} ", fg_color=0, bg_color=bg_color))
            if i < len(grouped) - 1:
                next_bg = grouped[i + 1][1] if i + 1 < len(grouped) else None
                if next_bg is not None:
                    result.append(apply_color(POWERLINE_RIGHT, fg_color=bg_color, bg_color=next_bg))
                else:
                    result.append(apply_color(POWERLINE_RIGHT, fg_color=bg_color))
            else:
                result.append(apply_color(POWERLINE_RIGHT, fg_color=bg_color, bg_color=0))
        return "".join(result)

    # Build final output — each inner list is one screen line
    if is_powerline and config["theme"] != "none":
        rendered = [
            _build_powerline_line(line_segs)
            for line_segs in segment_lines
            if line_segs
        ]
        result_str = "\n".join(rendered)
        if debug:
            total_segs = sum(len(l) for l in segment_lines)
            sys.stderr.write(
                f"DEBUG: Returning powerline output with {total_segs} segments across {len(rendered)} line(s)\n"
            )
        return result_str
    elif is_powerline:
        rendered = [" > ".join(line) for line in output_lines if line]
        result_str = "\n".join(rendered)
        if debug:
            sys.stderr.write(
                f"DEBUG: Returning powerline (no theme) output across {len(rendered)} line(s)\n"
            )
        return result_str
    else:
        non_empty = [line for line in output_lines if line]
        if len(non_empty) > 1 and non_empty[0]:
            # Hanging-indent continuation lines so the first "|" on each extra
            # line aligns vertically with the "|" after the first field on line 1.
            # Strip ANSI codes to measure the visual width of the first field.
            first_visible = re.sub(r"\033\[[0-9;]*m", "", non_empty[0][0])
            indent = " " * len(first_visible)
            rendered = [separator.join(non_empty[0])]
            for line in non_empty[1:]:
                rendered.append(indent + separator + separator.join(line))
        else:
            rendered = [separator.join(line) for line in non_empty]
        result_str = "\n".join(rendered)
        if debug:
            sys.stderr.write(
                f"DEBUG: Returning regular output across {len(rendered)} line(s)\n"
            )
        return result_str


def main() -> int:
    """Main entry point for the pyccsl status line generator.

    Parses arguments, reads JSON from stdin, computes metrics (cost,
    tokens, git status, performance), and prints the formatted status line.

    Returns:
        0 on success.
    """
    # Parse arguments
    config = parse_arguments()
    debug = config.get("debug", False)

    if debug:
        sys.stderr.write(f"DEBUG: Config: {config}\n")

    # Read input
    input_data = read_input()

    if debug:
        sys.stderr.write(f"DEBUG: Input data keys: {list(input_data.keys())}\n")
        sys.stderr.write(f"DEBUG: Model: {input_data.get('model', 'None')}\n")
        sys.stderr.write(
            f"DEBUG: Transcript path: {input_data.get('transcript_path', 'None')}\n"
        )
        sys.stderr.write(f"DEBUG: CWD: {input_data.get('cwd', 'None')}\n")

    # Extract model info
    model_info = extract_model_info(input_data)

    if debug:
        sys.stderr.write(f"DEBUG: Model info: {model_info}\n")

    # Get weekly limit for current model (if weekly-limit field is requested)
    if "weekly-limit" in config["fields"] and model_info.get("id"):
        weekly_limit = get_weekly_limit_for_model(model_info["id"], debug=debug)
        if weekly_limit:
            model_info["weekly_limit"] = weekly_limit
            if debug:
                sys.stderr.write(f"DEBUG: Weekly limit: {weekly_limit}\n")

    # Extract git status
    git_info = extract_git_status(input_data)

    if debug:
        sys.stderr.write(f"DEBUG: Git info: {git_info}\n")

    # Load transcript if provided
    transcript_path = input_data.get("transcript_path", None)
    transcript_entries = load_transcript(transcript_path, debug=debug)

    # Calculate metrics from transcript
    metrics = {}

    if debug:
        sys.stderr.write(
            f"DEBUG: Transcript entries loaded: {len(transcript_entries)}\n"
        )

    if transcript_entries:
        # Calculate token usage
        token_totals = calculate_token_usage(transcript_entries)
        metrics.update(token_totals)

        if debug:
            sys.stderr.write(f"DEBUG: Token totals: {token_totals}\n")

        current_ctx = get_current_context_size(transcript_entries)
        metrics["current_context_size"] = current_ctx

        # Derive the auto-compact threshold using the same formula as Claude Code
        # (code.claude.com/docs/en/env-vars, anthropics/claude-code issue #31806):
        #
        #   effective_window = min(CLAUDE_CODE_AUTO_COMPACT_WINDOW, model_window)
        #   default_threshold = effective_window - reserved_buffer
        #   if pct set:
        #       threshold = min(floor(effective_window * pct/100), default_threshold)
        #   else:
        #       threshold = default_threshold
        #
        # The Math.min clamp mirrors Claude Code: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
        # can only LOWER the trigger, never raise it above (window − buffer).
        model_window = config["context_window"]
        acw = config.get("auto_compact_window", 0)
        effective_window = min(acw, model_window) if acw > 0 else model_window
        reserved_buffer = config.get("compact_buffer", 13000)
        default_threshold = max(0, effective_window - reserved_buffer)

        if config.get("compact_threshold", 0) > 0:
            # Explicit absolute override wins over everything else
            compact_threshold = config["compact_threshold"]
        elif config.get("compact_pct", 0) > 0:
            # Percentage path: clamped so it can only lower the default threshold
            compact_threshold = min(
                int(effective_window * config["compact_pct"] / 100),
                default_threshold,
            )
        else:
            # No pct set → Claude Code default (effective window minus response buffer)
            compact_threshold = default_threshold

        if debug:
            sys.stderr.write(
                f"DEBUG: compact_threshold={compact_threshold} "
                f"(effective_window={effective_window}, pct={config.get('compact_pct')}, "
                f"buffer={reserved_buffer}, model_window={model_window})\n"
            )
        metrics["compact_remaining"] = max(0, compact_threshold - current_ctx)

        # Calculate cost (unless disabled or on Max plan)
        if not config.get("no_cost", False):
            # 2.0.1: Try to use pre-calculated cost if available
            if "cost" in input_data and isinstance(input_data["cost"], dict):
                cost = input_data["cost"].get("total_cost_usd", 0.0)
                if debug:
                    sys.stderr.write(
                        f"DEBUG: Using pre-calculated cost from 2.0.1: ${cost:.4f}\n"
                    )
            else:
                # Fallback: Calculate cost from transcript using per-entry models
                cost = calculate_total_cost(transcript_entries, debug=debug)
                if debug:
                    sys.stderr.write(
                        f"DEBUG: Calculated cost from transcript: ${cost:.4f}\n"
                    )

            metrics["cost"] = cost
            metrics["cost_formatted"] = format_cost(cost)
        elif debug:
            sys.stderr.write("DEBUG: Cost calculation disabled (--no-cost flag)\n")

        # Calculate performance metrics
        perf_metrics = calculate_performance_metrics(
            transcript_entries, token_totals, debug=debug
        )
        metrics.update(perf_metrics)

        # Calculate performance badge
        if "cache_hit_rate" in metrics:
            # Badge should be colored unless theme is "none"
            colored = config["theme"] != "none"
            is_powerline = config["style"] == "powerline"
            badge = calculate_performance_badge(
                metrics["cache_hit_rate"],
                config["cache_thresholds"],
                colored=colored,
                powerline=is_powerline,
                no_emoji=config["no_emoji"],
            )
            metrics["badge"] = badge
            if debug:
                sys.stderr.write(f"DEBUG: Badge created: {badge[:20]}...\n")
        elif debug:
            sys.stderr.write(
                "DEBUG: Badge not created - cache_hit_rate not in metrics\n"
            )

    # Add git info to metrics
    if git_info["branch"]:
        metrics["git_info"] = git_info

    # Add weekly limit to metrics (if available)
    if "weekly_limit" in model_info:
        metrics["weekly_limit"] = model_info["weekly_limit"]

    # Format and output (pass metrics for field display)
    output = format_output(config, model_info, input_data, metrics)
    # Only add reset if colors were used (to prevent terminal color bleed)
    if config["theme"] != "none":
        print(output + RESET)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
