import os
import re
import subprocess
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory

app = Flask(__name__)

BASE_PORT = 7681
MAX_SESSIONS = 10
active_sessions = {}  # name -> {'port': int, 'process': subprocess.Popen}

CLAUDE_MD_TEMPLATE = """\
# Analysis: {name}

## Working Directory
Your working directory is `/workspace/user_analysis/{name}`. Write all output files here.

## gmatbard Library
The `gmatbard` Python library is installed and importable.
- High-level API examples: `/gmatbard/examples/`
- Most complete real mission: `/gmatbard/examples/Aquila_DRM_sim1/phase1_5_724kg_800N280s_120mN1400s.py`
- GMAT HTML docs: `/gmatbard/docs/GMAT2025a/help/html/`

## Running GMAT Scripts
`GmatConsole` is on PATH. To run a .script file:
```python
from gmatbard.low_level.script_execution import GmatExecutor
result = GmatExecutor().execute('mission.script')
```

## Committing and Pushing Work
```bash
git -C /workspace add user_analysis/{name}/
git -C /workspace commit -m "description of what was done"
git -C /workspace push
```

## Scope
- Write files only inside this analysis folder.
- Read examples and docs from /gmatbard/ freely.
- Do not modify files outside /workspace/user_analysis/{name}/.
"""


def seed_claude_md(name, analysis_path):
    claude_md_path = os.path.join(analysis_path, 'CLAUDE.md')
    if not os.path.exists(claude_md_path):
        with open(claude_md_path, 'w') as f:
            f.write(CLAUDE_MD_TEMPLATE.format(name=name))


def get_next_port():
    used = {s['port'] for s in active_sessions.values()}
    for p in range(BASE_PORT, BASE_PORT + MAX_SESSIONS):
        if p not in used:
            return p
    return None


def spawn_ttyd(name, analysis_path):
    port = get_next_port()
    if port is None:
        return None
    cmd = [
        'ttyd', '-p', str(port), '--writable',
        'bash', '-c',
        f'cd {analysis_path} && exec claude'
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    active_sessions[name] = {'port': port, 'process': proc}
    return port


def ensure_session(name):
    """Start a ttyd session for name if not already running."""
    if name in active_sessions:
        proc = active_sessions[name]['process']
        if proc.poll() is None:  # still running
            return active_sessions[name]['port']
        else:
            del active_sessions[name]
    analysis_path = f'/workspace/user_analysis/{name}'
    os.makedirs(analysis_path, exist_ok=True)
    seed_claude_md(name, analysis_path)
    return spawn_ttyd(name, analysis_path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/open', methods=['POST'])
def open_analysis():
    name = request.form.get('name', '')
    # Sanitize: strip whitespace, replace spaces with underscores, keep only alphanumeric/underscore/hyphen
    name = name.strip().replace(' ', '_')
    name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
    if not name:
        return redirect(url_for('index'))

    analysis_path = f'/workspace/user_analysis/{name}'
    os.makedirs(analysis_path, exist_ok=True)
    seed_claude_md(name, analysis_path)

    # Spawn ttyd if not already running
    ensure_session(name)

    return redirect(url_for('workspace', name=name))


@app.route('/workspace/<name>')
def workspace(name):
    port = ensure_session(name)
    return render_template('workspace.html', name=name, port=port)


@app.route('/api/files/<name>')
def api_files(name):
    base_path = f'/workspace/user_analysis/{name}'
    if not os.path.isdir(base_path):
        return jsonify([])

    entries = []
    for dirpath, dirnames, filenames in os.walk(base_path):
        # Add directories
        for dirname in dirnames:
            abs_path = os.path.join(dirpath, dirname)
            rel_path = os.path.relpath(abs_path, base_path)
            entries.append({
                'path': rel_path,
                'size': 0,
                'is_dir': True
            })
        # Add files
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, base_path)
            try:
                size = os.path.getsize(abs_path)
            except OSError:
                size = 0
            entries.append({
                'path': rel_path,
                'size': size,
                'is_dir': False
            })

    # Sort: directories first, then files, both alphabetically
    entries.sort(key=lambda e: (not e['is_dir'], e['path'].lower()))
    return jsonify(entries)


@app.route('/files/<name>/<path:filepath>')
def serve_file(name, filepath):
    base_path = f'/workspace/user_analysis/{name}'
    inline_extensions = {'.txt', '.py', '.script', '.log', '.md'}
    _, ext = os.path.splitext(filepath)
    if ext.lower() in inline_extensions:
        return send_from_directory(base_path, filepath, mimetype='text/plain')
    else:
        return send_from_directory(base_path, filepath, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
