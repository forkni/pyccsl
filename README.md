# pyccsl — Python Claude Code Status Line

A customizable status bar generator for [Claude Code](https://claude.ai/code) that shows live session metrics, git context, model info, and auto-compact countdowns — all in a single terminal line.

```
C:\myproject | Sonnet 4.6 | Cache: 87% | Session: 43m | Messages: 62 | Tok: 98.2K | Cmpct: 501.8K
```

## Features

- **Live context tokens** — matches the same value Claude Code watches for auto-compact
- **Auto-compact countdown** — exact replica of Claude Code's compaction formula including `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`
- **Drive-letter aware folders** — shows `C:\project` vs `G:\project` to disambiguate mirrored paths on different Windows drives
- **Git branch + dirty flag** — branch name with `*` when uncommitted changes exist
- **Multi-theme support** — 9 built-in color themes (Nord, Dracula, Gruvbox, Tokyo Night, Catppuccin, Solarized, Minimal, and more)
- **Multiple separator styles** — powerline arrows, pipes, dots, simple spaces
- **Session performance** — cache hit rate, session duration, message count
- **Cost tracking** — per-session USD cost based on live Anthropic pricing
- **Weekly limit gauge** — percentage of your monthly/weekly spend limit consumed
- **No dependencies** — pure Python 3 stdlib only

## Requirements

- Python 3.10+
- Claude Code (any recent version)
- Windows (installer script); pyccsl.py itself works on any platform

## Quick Install (Windows)

1. Clone this repository or [download the ZIP](../../archive/refs/heads/main.zip) and extract it
2. Double-click **`install.cmd`**
3. Choose your context window size when prompted
4. Restart Claude Code

The installer copies `pyccsl.py` to `%USERPROFILE%\.claude\` and writes the `statusLine` entry into your global `settings.json`.

## Manual Installation

1. Copy `pyccsl.py` to `%USERPROFILE%\.claude\` (or any stable location)
2. Add this block to `%USERPROFILE%\.claude\settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "python C:/Users/YOUR_NAME/.claude/pyccsl.py folder,git,model,perf-cache-rate,perf-session-time,perf-message-count,tokens,compact-remaining --style pipes --no-emoji --context-window 200000"
}
```

Replace `YOUR_NAME` with your Windows username, and adjust `--context-window` to match your model:

| Model family | `--context-window` |
|---|---|
| Haiku / Sonnet (standard) | `200000` |
| Sonnet with extended context | `200000` |
| Opus 1M extended context | `1000000` |

## Usage

```
python pyccsl.py [FIELDS] [OPTIONS]
```

### Fields

Specify a comma-separated list of fields as the first positional argument:

| Field | Description |
|---|---|
| `badge` | Fixed `CC` label (Claude Code marker) |
| `folder` | Current directory name with drive letter on Windows (e.g. `C:\myproject`) |
| `git` | Git branch name + `*` dirty indicator |
| `model` | Short model name (e.g. `Sonnet 4.6`) |
| `weekly-limit` | Weekly spend limit consumed as a percentage |
| `perf-cache-rate` | Prompt cache hit rate for the session |
| `perf-session-time` | Session wall-clock duration |
| `perf-message-count` | Number of assistant messages in the session |
| `perf-all-metrics` | All three perf metrics in one segment |
| `input` | Cumulative input tokens |
| `output` | Cumulative output tokens |
| `tokens` | **Live** context window usage — reads `context_window.total_input_tokens` from Claude Code's stdin JSON (CC v2.1.132+); falls back to transcript for older versions |
| `compact-remaining` | Tokens until auto-compact triggers |
| `cost` | Session cost in USD |
| `newline` | Line break (splits output across two lines) |

**Default field order** (when none specified): `badge,folder,git,model,weekly-limit,perf-cache-rate,perf-session-time,perf-message-count,input,output,tokens,compact-remaining,cost`

### Separator Styles

| `--style` | Example |
|---|---|
| `powerline` | ` myproject  main  Sonnet 4.6 ` (requires Nerd Font) |
| `arrows` | `myproject > main > Sonnet 4.6` |
| `pipes` | `myproject \| main \| Sonnet 4.6` |
| `dots` | `myproject · main · Sonnet 4.6` |
| `simple` | `myproject  main  Sonnet 4.6` |

### Color Themes

| `--theme` | Description |
|---|---|
| `default` | Terminal default colors |
| `solarized` | Solarized palette |
| `nord` | Nord palette |
| `dracula` | Dracula palette |
| `gruvbox` | Gruvbox warm palette |
| `tokyo` | Tokyo Night palette |
| `catppuccin` | Catppuccin Mocha palette |
| `minimal` | Muted monochrome |
| `none` | No colors |

### CLI Options

| Option | Default | Description |
|---|---|---|
| `--style STYLE` | `powerline` | Separator style (see above) |
| `--theme THEME` | `default` | Color theme (see above) |
| `--numbers FORMAT` | `human` | Number format: `human` (1.2K), `full` (1200), `compact` (1.2K) |
| `--context-window N` | `200000` | Model context window in tokens |
| `--auto-compact-window N` | `0` | Mirrors `CLAUDE_CODE_AUTO_COMPACT_WINDOW`; 0 = use `--context-window` |
| `--compact-pct N` | `0` | Mirrors `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`; 0 = read from env |
| `--compact-threshold N` | `0` | Absolute token threshold override (0 = derive from formula) |
| `--compact-buffer N` | `13000` | Response reserve subtracted from window on the default path |
| `--no-emoji` | off | Replace emoji prefixes with short text labels |
| `--no-color` | off | Disable ANSI color codes |
| `--no-git` | off | Skip git status (faster in large repos) |
| `--debug` | off | Print diagnostic JSON to stderr |
| `--version` | — | Print version and exit |

### Environment Variables

pyccsl reads Claude Code's official env vars automatically when they are set in your shell or `settings.json`:

| Variable | Description |
|---|---|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Effective context window for compaction math (official CC var) |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Compaction trigger as % of effective window (official CC var) |

Additional `PYCCSL_*` variables that mirror the CLI flags (useful in `settings.json` `env` block without touching the command string):

| Variable | Mirrors |
|---|---|
| `PYCCSL_THEME` | `--theme` |
| `PYCCSL_STYLE` | `--style` |
| `PYCCSL_NUMBERS` | `--numbers` |
| `PYCCSL_CONTEXT_WINDOW` | `--context-window` |
| `PYCCSL_AUTO_COMPACT_WINDOW` | `--auto-compact-window` |
| `PYCCSL_COMPACT_THRESHOLD` | `--compact-threshold` |
| `PYCCSL_COMPACT_BUFFER` | `--compact-buffer` |

## How Auto-Compact Math Works

pyccsl replicates Claude Code's compaction formula exactly:

```
effective_window = min(CLAUDE_CODE_AUTO_COMPACT_WINDOW, context_window_size)
                   # context_window_size = model's full window from stdin (e.g. 200000 or 1000000)
                   # if CLAUDE_CODE_AUTO_COMPACT_WINDOW is 0/unset → use context_window_size

default_threshold = effective_window - compact_buffer   # buffer default: 13000

if CLAUDE_AUTOCOMPACT_PCT_OVERRIDE is set:
    threshold = min(floor(effective_window × pct / 100), default_threshold)
    # pct can only LOWER the trigger, never raise it above the default

compact_remaining = max(0, threshold - live_context_tokens)
```

`live_context_tokens` comes from `context_window.total_input_tokens` in Claude Code's stdin JSON
(CC v2.1.132+), falling back to transcript reconstruction for older versions.

**Important:** `context_window.used_percentage` in the stdin JSON always reflects
`total_input_tokens / context_window_size` (model's full window), not relative to
`CLAUDE_CODE_AUTO_COMPACT_WINDOW`. When `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is smaller than the
model window, the compact fires below 100 × pct % — pyccsl uses `total_input_tokens` directly
rather than deriving context from `used_percentage` to avoid this ambiguity.

**Example** with `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80`, 1M model:
- `effective_window = min(500000, 1000000) = 500000`
- `default_threshold = 500000 - 13000 = 487000`
- `threshold = min(floor(500000 × 0.80), 487000) = min(400000, 487000) = 400000`
- If current context = 98200 tokens → `compact_remaining = 400000 - 98200 = 301800`

## Input Format

pyccsl reads a JSON object from stdin. Claude Code passes this automatically when `statusLine.type` is `"command"`. The JSON contains the session transcript path, model info, usage stats, and git context. Relevant fields for context math:

| Field | Description |
|---|---|
| `context_window.total_input_tokens` | Live context size in tokens (= `current_usage` sum). Used for `Tok` and `Cmpct`. |
| `context_window.context_window_size` | Model's actual window: 200000 (standard) or 1000000 (extended context). Not affected by `CLAUDE_CODE_AUTO_COMPACT_WINDOW`. |
| `context_window.used_percentage` | `total_input_tokens / context_window_size × 100`. Useful for display; pyccsl does not use it for compact math. |
| `context_window.current_usage` | Per-component breakdown (input, cache_creation, cache_read). Sum always equals `total_input_tokens`. |

## License, provenance and trademarks

**License.** pyccsl is released under the [MIT License](LICENSE).
Copyright (c) 2025-2026 Alexander Korneev.

**AI-assisted authorship.** Parts of this project's code and documentation were drafted
with the help of Claude Code, an AI coding assistant. The author reviewed, edited,
tested, selected and arranged that material and is responsible for it. No copyright is
claimed over raw, unedited AI output.

**Contributions.** Under
[GitHub's Terms of Service, section D.6](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#6-contributions-under-repository-license),
anything you contribute to this repository is licensed to the project and its users
under the repository's MIT License ("inbound = outbound"). No separate contributor
agreement or sign-off is required.

**Trademarks.** Claude and Claude Code are trademarks of Anthropic, PBC. These names are
used only to identify the software pyccsl works with. pyccsl is an independent project
and is not affiliated with, sponsored by or endorsed by Anthropic.
