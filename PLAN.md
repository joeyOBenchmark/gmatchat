# gmatchat — Implementation Plan

## What This Is

A locally hosted web app where a user can open a browser, name an analysis, and chat with Claude Code to design and run GMAT missions. The LLM writes and executes Python scripts using the `gmatbard` library from `../05_gmatbard`, and results are stored in a per-analysis folder that the user can browse and download from the same page.

---

## Repository Layout

```
06_gmatchat/
├── Dockerfile
├── docker-compose.yml
├── .env.example              # ANTHROPIC_API_KEY placeholder
├── app/
│   ├── server.py             # Flask app
│   ├── templates/
│   │   ├── index.html        # Landing page — analysis name picker
│   │   └── workspace.html    # Workspace — file tree + terminal iframe
│   └── static/
│       └── style.css
└── user_analysis/            # git-tracked; one subfolder per analysis
    └── .gitkeep
```

---

## Container Volumes

| Host path | Container path | Access |
|---|---|---|
| `./` (this repo) | `/workspace` | read-write — git repo root lives here |
| `../05_gmatbard` | `/gmatbard` | read-only |
| `/home/joeyoberholtzer/installs/gmat-ubuntu-x64-R2025a/GMAT/R2025a` | `/gmat` | read-only |

The GMAT binary at `/gmat/bin/GmatConsole` is added to `PATH` inside the container. The `GMAT_PATH` env var is set to `/gmat`.

---

## Ports

| Port | Purpose |
|---|---|
| `8080` | Flask web UI |
| `7681–7690` | ttyd terminal instances (one per active analysis, up to 10) |

ttyd WebSocket connections go browser → container directly; Flask does not proxy them.

---

## Scope Limiting

The container has two user accounts:

- **root** — runs Flask; owns `/workspace/app/` and `/gmatbard/`
- **claude** — runs every `claude` session; can only write to its assigned analysis folder

Session start sequence (handled by Flask):
1. Create `/workspace/user_analysis/<name>/` if it does not exist
2. `chown -R claude:claude /workspace/user_analysis/<name>/`
3. Seed a `CLAUDE.md` inside the folder (see below)
4. Spawn a ttyd process on the next available port in `7681–7690`:
   ```
   ttyd -p <port> --writable su -s /bin/bash -c \
     "claude --cwd /workspace/user_analysis/<name> --add-dir /gmatbard" claude
   ```

The `claude` user cannot write outside its analysis folder because it does not own anything else on the writable volume.

---

## Seeded CLAUDE.md (per analysis folder)

Each new analysis folder gets a `CLAUDE.md` that tells the LLM:

- Its working directory is this analysis folder; keep all outputs here
- The `gmatbard` library is installed and importable; examples are in `/gmatbard/examples/`
- GMAT docs are in `/gmatbard/docs/GMAT2025a/help/html/`
- `GmatConsole` is on PATH; use `gmatbard.low_level.script_execution.GmatExecutor` to run scripts
- Commit work with `git -C /workspace add user_analysis/<name>/<file> && git -C /workspace commit`
- Git user is pre-configured in the container

---

## User Experience Flow

1. User visits `http://localhost:8080`
2. Single text field: **Analysis name** (browser `autocomplete` surfaces previous entries for free)
3. User submits → Flask creates the folder, spawns ttyd, redirects to `/workspace/<name>`
4. Workspace page layout:
   - **Left panel** — file tree of `user_analysis/<name>/`, auto-refreshes every few seconds; each file has a download link; text/script files can be viewed inline
   - **Right panel** — ttyd `<iframe>` taking up the rest of the viewport; Claude Code is running and ready
5. Returning to an existing analysis resumes it (folder already exists, new ttyd session starts in the same folder)

---

## Dockerfile Highlights

- Base: `ubuntu:22.04`
- Installs: Python 3.11, pip, Node.js 20, `npm install -g @anthropic-ai/claude-code`, ttyd binary, git, `useradd claude`
- Copies `app/` to `/workspace/app/`
- Installs gmatbard in dev mode: `pip install -e /gmatbard`
- Sets `GMAT_PATH=/gmat` and adds `/gmat/bin` to `PATH`
- Configures a minimal git identity for the `claude` user
- Entrypoint: starts Flask on `0.0.0.0:8080`

---

## What Is Out of Scope (for this demo)

- Authentication / multi-user isolation beyond filesystem permissions
- Persistent ttyd process management across container restarts (sessions are ephemeral; files are not)
- HTTPS
- Analysis deletion from the UI
