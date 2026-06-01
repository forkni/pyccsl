# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

pyccsl (Python Claude Code Status Line) is a single-file, zero-dependency (Python 3.10+ stdlib only) tool that renders Claude Code's terminal status bar. Claude Code invokes it on every status-line refresh, piping a JSON object to **stdin**; pyccsl prints one or more formatted lines to stdout. It never calls the Anthropic API — it is a passive reporter that reads Claude Code's own session transcript and replicates Claude Code's internal auto-compact math.

The entire program is `pyccsl.py`. `install.cmd` is a Windows-only deployer; `README.md` is the user-facing reference. There is no packaging, test suite, lint config, or CI — do not assume `pytest`/`ruff`/`make` exist.

## Running and debugging

There is no build step. Run the script directly, feeding it a JSON object on stdin:

```sh
echo '{"model":{"id":"claude-sonnet-4-6"},"workspace":{"current_dir":"C:/proj"},"transcript_path":"..."}' | python pyccsl.py folder,model,tokens
echo '{}' | python pyccsl.py --debug folder,model,tokens   # prints diagnostic JSON to stderr
```

The current version is stored in `__version__` near the top of `pyccsl.py`. There is no `--version` flag.

Exit codes: 0 success, 1 config/arg error, 2 input/JSON error (incl. stdin is a TTY), 3 file access (reserved), 4 runtime (reserved).

Install/deploy (Windows): `install.cmd` copies `pyccsl.py` to `%USERPROFILE%\.claude\pyccsl.py` and writes a `statusLine` entry into `%USERPROFILE%\.claude\settings.json`. The script itself is cross-platform; only the installer is Windows-specific.

## Execution flow (in `pyccsl.py`)

`main()` (~line 1680) drives the pipeline:

1. **`parse_arguments()`** merges config with precedence **`--env` file > `PYCCSL_*` env vars > CLI/defaults**. `parse_env_file()` only honors `PYCCSL_`-prefixed keys (deliberate security guard). The two official `CLAUDE_CODE_AUTO_COMPACT_WINDOW` / `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` env vars feed in as flag *defaults* — this is how pyccsl stays in sync with Claude Code's global settings.
2. **`read_input()`** parses the stdin JSON.
3. **Extraction** (`extract_model_info`, `extract_workspace_info`, `extract_git_status` — the last shells out to `git`). These handle **two input schemas**: a legacy format and the newer "2.0.1" format (`workspace.current_dir`, `model.info`, top-level `cost`). This dual-schema handling is a cross-cutting concern — preserve both paths when editing extraction.
4. **`load_transcript()`** reads the Claude Code transcript **JSONL** file (path from `transcript_path`). Cumulative metrics (I/O counts, cost, session time, cache-hit rate) come from this file. The **live context size** for `tokens` and `compact-remaining` comes from stdin's `context_window` object (step 5).
5. **`extract_context_window()`** reads `context_window.total_input_tokens` (live context in tokens, equals `current_usage` sum), `context_window.context_window_size` (model's actual window — always 200K or 1M, never changed by `CLAUDE_CODE_AUTO_COMPACT_WINDOW`), and `context_window.used_percentage`. Falls back to transcript's `get_current_context_size()` when absent. When `--context-window` is 0, `context_window_size` from stdin overrides the model-ID lookup; only when stdin lacks it does `get_model_context_window()` prefix-match against `MODEL_CONTEXT_WINDOWS`.
6. **Auto-compact math** (inlined in `main()`): `effective_window = min(CLAUDE_CODE_AUTO_COMPACT_WINDOW, context_window_size)`; `threshold = min(floor(effective_window x pct/100), effective_window - buffer)` (buffer default 13000, pct clamped so it can only *lower* the trigger — mirrors Claude Code's `Math.min`); `compact_remaining = max(0, threshold - current_context)`. When `CLAUDE_CODE_AUTO_COMPACT_WINDOW` < model window, compact fires below PCT% of `used_percentage` (the two are decoupled); pyccsl uses `total_input_tokens` directly rather than deriving context from `used_percentage` to avoid this ambiguity.
7. **Cost:** prefers precomputed `cost.total_cost_usd` (2.0.1 schema); else `calculate_total_cost()` walks the transcript, attributing tokens to the correct model via a `uuid -> entry` parent lookup, priced against `PRICING_DATA`.
8. **`format_output()`** renders. It iterates the canonical `FIELD_ORDER` (not the user's listed order), builds a list of lines (`newline` pseudo-field starts a new line), and has two paths: a plain/themed string-separator path and a powerline path (`_build_powerline_line`) using arrows with matched fg/bg.

## Critical distinction: live context vs session totals

Three token computations feed different fields — do not conflate them:

- **`context_window.total_input_tokens`** from stdin (CC v2.1.132+) = the live context window occupancy from the most recent API response. This is what CC uses for its own `used_percentage` and auto-compact check. The `tokens` and `compact-remaining` fields prefer this source. Always equals `current_usage.input_tokens + cache_creation_input_tokens + cache_read_input_tokens`.
- **`get_current_context_size()`** = fallback for older CC: reads the **last assistant entry's** usage from the transcript JSONL. Used only when `context_window` is absent/null in stdin.
- **`calculate_token_usage()`** **sums across the whole session** (cumulative I/O display, cache-hit-rate). Do not use this for live-context math.

## Module-level config tables (where most edits land)

- **`PRICING_DATA`** — per-model USD rates per million tokens.
- **`MODEL_CONTEXT_WINDOWS`** — model-ID-prefix -> context window. **Update this when Anthropic ships new model IDs** (e.g. `claude-sonnet-4-6` and `claude-opus-4-5`+ map to 1,000,000; older 4.x and all 3.x map to 200,000; unknown falls back to 200,000). In practice, `context_window_size` from stdin is now the primary source, so this table is a fallback only.
- **`THEMES`** — 9 palettes of 256-color ANSI codes.
- **`DEFAULT_FIELDS`** / **`FIELD_ORDER`** — `FIELD_ORDER` is authoritative for display sequence regardless of user-supplied field order.

## Other non-obvious behavior

- Weekly limits are not from any API — `get_weekly_limit_for_model()` reads a manually maintained `~/.claude/weekly_limits.json`.
- `__version__` is defined near the top of `pyccsl.py`; bump it and update `MODEL_CONTEXT_WINDOWS`/`PRICING_DATA` as the main maintenance tasks when new Claude models ship.
- The README "How Auto-Compact Math Works" section documents the formula that must stay in sync with execution-flow step 6 above.
- `context_window_size` from stdin is always the model's actual window (200K standard, 1M extended). `CLAUDE_CODE_AUTO_COMPACT_WINDOW` limits the effective window for compact math but does NOT change `context_window_size` or `used_percentage` in stdin.
