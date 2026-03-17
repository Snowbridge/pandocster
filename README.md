# Pandocster

Pandocster is a CLI helper around [pandoc](https://pandoc.org/) workflows. It builds a single document (PDF, HTML, and other formats) from a tree of Markdown files with minimal configuration.

## Quick start

```bash
pandocster init ./my-doc          # scaffold a new project directory
cd my-doc
pandocster check                  # verify pandoc & Lua versions
pandocster build src/ --to docx   # build a Word document
```

The resulting DOCX (or other format) is written in the current directory; the default output name is derived from the current working directory unless you pass `--file-name`.

## What it does

- **Init** — `pandocster init [dir]` scaffolds a new project directory: creates `pandocster.yaml`, the source tree (`src/md/`, `src/assets/`, `src/templates/`), and a ready-to-run `generate.sh` build script.
- **Build** — Runs pandoc on the prepared tree with configurable options, metadata, and Lua filters. Includes built-in filters: `absorb_nonvisual_paragraphs`, `header_offset`, `link_anchors`, `newpage`. During the preparation stage `Pandocster` builds a staging tree from a source Markdown directory: copies files, injects header-offset and anchor comments for structure, rewrites image links into a shared `resources/` directory, and preprocesses reference-style links. Pass `--prepared` to skip the preparation stage and reuse a build directory preserved by a previous `--preserve-build` run — useful when building the same content into multiple formats without repeating identical preparation work.
- **Check** — `pandocster check` verifies that pandoc (≥3.8.3) and its Lua engine (≥5.4) are installed and sufficient.
- **Config** — Optional `pandocster.yaml` in the project directory or `~/.config/pandocster/config.yaml` globally. Use `pandocster config show` to print the effective config and `pandocster config create` to write a `pandocster.yaml` in the current directory.

## How it works

1. Run `pandocster init [dir]` once to scaffold the project structure and config.
2. Write your Markdown files under `src/md/` (nested directories are supported).
3. Run `pandocster build src/ --to <format>` (e.g. `pdf`, `html`, `docx`) to get a standalone file. Or just run the generated `./generate.sh`.
4. Config is loaded from the current directory (`pandocster.yaml`), then global config, then built-in defaults.
5. **Build** collects all `.md` files under the build directory (with `_index.md` first per directory), runs pandoc with the configured filters and metadata, and writes the output in the current working directory as `<file-name>.<format>`. The build directory is removed after a successful run unless you pass `--preserve-build`.

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

| Command                                                   | Description                                                                                     |
|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `pandocster init [dir] [--force]`                         | Scaffold a project directory with config and src tree                                           |
| `pandocster check`                                        | Verify pandoc and Lua versions                                                                  |
| `pandocster build <src> [build] --to <format>`            | Prepare and render a document (e.g. `--to pdf`)                                                 |
| `pandocster build <src> [build] --to <format> --prepared` | Skip prepare step; reuse a build directory preserved by a previous run (see `--preserve-build`) |
| `pandocster config show`                                  | Print effective config as YAML                                                                  |
| `pandocster config create [--global] [--force]`           | Write config file locally or globally                                                           |

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
pandocster init ./test-doc                # scaffold a new project in ./test-doc
pandocster init ./test-doc --force        # re-initialize even if directory is not empty
pandocster config show
pandocster config create
pandocster config create --force          # overwrite without prompting
pandocster config create --global         # write ~/.config/pandocster/config.yaml
pandocster config create --global --force # overwrite global config
pandocster build src/ --to docx           # full build (prepare + pandoc)
pandocster build src/ --to docx --prepared # skip prepare, use src as-is
```
