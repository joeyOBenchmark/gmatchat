#!/bin/bash
set -e

git config --global --add safe.directory /workspace

# Configure git to authenticate to GitHub using the runtime token.
# This enables `git push` from inside the container.
if [ -n "${GITHUB_TOKEN}" ]; then
    git config --global credential.helper store
    echo "https://x-access-token:${GITHUB_TOKEN}@github.com" > /root/.git-credentials
    chmod 600 /root/.git-credentials

    # If the workspace remote is SSH, rewrite it to HTTPS so the token works.
    REMOTE_URL=$(git -C /workspace remote get-url origin 2>/dev/null || true)
    if echo "${REMOTE_URL}" | grep -q "git@github.com:"; then
        HTTPS_URL=$(echo "${REMOTE_URL}" | sed 's|git@github.com:|https://github.com/|')
        git -C /workspace remote set-url origin "${HTTPS_URL}"
    fi
fi

exec python3 /workspace/app/server.py
