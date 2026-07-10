#!/bin/bash
set -e

# Bind mounts preserve the host's NUMERIC uid/gid, so on a machine where the
# host user isn't uid 1000 the workspace (including .git) appears owned by a
# uid the container's `claude` user doesn't match -- leaving claude unable to
# write the git index. Rather than chown the host's files (which would lock the
# host user out), remap `claude` to match whoever owns the mounted workspace.
HOST_UID=$(stat -c '%u' /workspace)
HOST_GID=$(stat -c '%g' /workspace)
if [ "${HOST_GID}" != "$(id -g claude)" ]; then
    groupmod -o -g "${HOST_GID}" claude
fi
if [ "${HOST_UID}" != "$(id -u claude)" ]; then
    usermod -o -u "${HOST_UID}" claude
fi
# Re-align claude's home/config (created at build time under the old uid, plus
# the mounted claude_config volume) to the remapped ids.
chown -R "${HOST_UID}:${HOST_GID}" /home/claude

# Fix ownership of user_analysis so claude can write there.
# Handles directories created by older root-based runs.
chown -R claude:claude /workspace/user_analysis

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
