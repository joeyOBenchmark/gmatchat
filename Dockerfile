# syntax=docker/dockerfile:1
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-venv \
    git \
    curl \
    wget \
    sudo \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
    -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd

RUN npm install -g @anthropic-ai/claude-code

RUN pip install flask

RUN useradd -m -s /bin/bash claude

RUN su -c 'git config --global user.email "claude@gmatchat.local"' claude \
    && su -c 'git config --global user.name "Claude"' claude

ENV GMAT_PATH=/gmat
ENV PATH="/gmat/bin:${PATH}"
ENV PYTHONPATH=/gmatbard

# Clone gmatbard and install its runtime dependencies.
# We set PYTHONPATH rather than `pip install` because the pyproject.toml
# metadata is incomplete and misses subpackages.
RUN --mount=type=secret,id=gmatbard_github_token \
    git clone https://$(cat /run/secrets/gmatbard_github_token)@github.com/joeyOBenchmark/gmatbard.git /gmatbard \
    && pip install numpy pandas matplotlib

RUN mkdir -p /workspace/user_analysis

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
