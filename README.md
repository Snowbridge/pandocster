# Pandocster

Pandocster is a CLI helper around [pandoc](https://pandoc.org/) workflows. It builds a single document (PDF, HTML, and other formats) from a tree of Markdown files with minimal configuration.

## Quick start

```bash
$ pandocster check
$ pandocster build ./docs/md --to docx
```

The resulting DOCX (or other format) is written in the current directory; the default output name is derived from the current working directory unless you pass `--file-name`.

## What it does

- **Build** — Runs pandoc on the prepared tree with configurable options, metadata, and Lua filters. Includes built-in filters: `absorb_nonvisual_paragraphs`, `header_offset`, `link_anchors`, `newpage`. During preparation stage `Pandocster` builds a staging tree from a source Markdown directory: copies files, injects header-offset and anchor comments for structure, rewrites image links into a shared `resources/` directory, and preprocesses reference-style links.
- **Check** — `pandocster check` verifies that pandoc (≥3.8.3) and its Lua engine (≥5.4) are installed and sufficient.
- **Config** — Optional `pandocster.yaml` in the project directory or `~/.config/pandocster/config.yaml` globally. Use `pandocster config show` to print the effective config and `pandocster config create` to write a `pandocster.yaml` in the current directory.

## How it works

1. You simply run `pandocster build <src> --to <format>` (e.g. `pdf`, `html`) and you get standalone file.
2. Config is loaded from the current directory (`pandocster.yaml`), then global config, then built-in defaults.
3. **Build** collects all `.md` files under the build directory (with `_index.md` first per directory), runs pandoc with the configured filters and metadata, and writes the output in the current working directory as `<file-name>.<format>`. The build directory can be removed after success unless you pass `--preserve-build`.

## Installation

Install Pandocster with **pipx** so the tool runs in an isolated environment and the `pandocster` command is available globally:

```bash
pipx install pandocster
```

From a local clone:

```bash
pipx install .
```

You must have **pandoc** (and its built-in Lua engine) installed separately. Run `pandocster check` to verify versions.

- **Windows**: `winget install JohnMacFarlane.Pandoc`
- **Debian**: `sudo apt install pandoc.`
- **RHEL**: `# dnf install pandoc.`
- **Arch**: `pacman -S pandoc.`

And there are more ways to install, please refer to official documentation [https://pandoc.org/installing.html](https://pandoc.org/installing.html).

## Requirements

- Python ≥3.10
- pandoc ≥3.8.3 with Lua ≥5.4

## Commands


| Command                                         | Description                                     |
| ----------------------------------------------- | ----------------------------------------------- |
| `pandocster check`                              | Verify pandoc and Lua versions                  |
| `pandocster build <src> [build] --to <format>`  | Prepare and render a document (e.g. `--to pdf`) |
| `pandocster config show`                        | Print effective config as YAML                  |
| `pandocster config create [--global] [--force]` | Write config file locally or globally           |


## Development

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash)
source .venv/bin/activate     # macOS / Linux
```

### 2. Install the project in editable mode with dev dependencies

```bash
pip install -e ".[dev]"
```

The `-e` flag makes changes in `src/` immediately available without reinstalling.

### 3. Run the test suite

```bash
pytest
```

### 4. Verify the CLI works

```bash
pandocster --help
pandocster check
pandocster config show
pandocster config create
pandocster config create --force          # overwrite without prompting
pandocster config create --global         # write ~/.config/pandocster/config.yaml
pandocster config create --global --force # overwrite global config
```

