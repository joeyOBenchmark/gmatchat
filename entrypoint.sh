#!/bin/bash
set -e

# Fix ownership of user_analysis so claude can write there.
# Handles directories created by older root-based runs.
chown -R claude:claude /workspace/user_analysis

# claude runs with a non-1000 uid so it cannot modify the host-owned source
# tree. Give it ownership of .git so the per-analysis git commit/push workflow
# still works. The working-tree source files stay owned by the host user and
# remain read-only to claude.
chown -R claude:claude /workspace/.git

# Configure git for both root (for remote rewriting below) and the claude user
git config --global --add safe.directory /workspace
gosu claude git config --global --add safe.directory /workspace

if [ -n "${GITHUB_TOKEN}" ]; then
    gosu claude git config --global credential.helper store
    echo "https://x-access-token:${GITHUB_TOKEN}@github.com" > /home/claude/.git-credentials
    chmod 600 /home/claude/.git-credentials
    chown claude:claude /home/claude/.git-credentials

    REMOTE_URL=$(git -C /workspace remote get-url origin 2>/dev/null || true)
    if echo "${REMOTE_URL}" | grep -q "git@github.com:"; then
        HTTPS_URL=$(echo "${REMOTE_URL}" | sed 's|git@github.com:|https://github.com/|')
        git -C /workspace remote set-url origin "${HTTPS_URL}"
    fi
fi

# Seed default claude settings into the persistent volume on first run
if [ ! -f /home/claude/.claude/settings.json ]; then
    mkdir -p /home/claude/.claude
    cat > /home/claude/.claude/settings.json << 'EOF'
{
  "theme": "dark",
  "skipAutoPermissionPrompt": true,
  "permissions": {
    "defaultMode": "auto"
  }
}
EOF
    chown -R claude:claude /home/claude/.claude
fi

# Drop privileges and start Flask as the claude user
exec gosu claude python3 /workspace/app/server.py
