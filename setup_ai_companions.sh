#!/bin/bash

# SME AI Auditor - AI Companion Setup Script (uv Optimized)
# Cleaned version using existing .env.template

set -e

echo "-------------------------------------------------------"
echo "🚀 Initializing SME AI Auditor Environment..."
echo "-------------------------------------------------------"

# 1. Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo "✅ uv is already installed."
fi

# 2. Setup Virtual Environment
echo "🐍 Creating virtual environment..."
uv venv
source .venv/bin/activate

# 3. Install Dependencies
# Pinned to 2.84.0+ for CVE-2026-24009 security patch as evaluated 
echo "📦 Installing project dependencies..."
uv pip install "docling>=2.84.0" qdrant-client haystack-ai \
               mistralai langfuse pytest weasyprint jinja2 structlog

# 4. Install Aider (Isolated Tool)
echo "📦 Installing Aider as an isolated tool..."
if ! command -v aider &> /dev/null; then
    uv tool install aider-chat
else
    echo "✅ Aider is already installed."
fi

# 5. Install Goose CLI (Binary)
# Using the corrected 2026 stable installer to avoid 404 errors
if ! command -v goose &> /dev/null; then
    echo "📦 Installing Goose CLI..."
    curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash
    export PATH="$HOME/.local/bin:$PATH"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
else
    echo "✅ Goose is already installed."
fi

# 6. Handle .env Configuration
if [ ! -f .env ]; then
    if [ -f .env.template ]; then
        echo "📄 Creating .env from .env.template..."
        cp .env.template .env
        echo "✅ .env created successfully."
    else
        echo "❌ Error: .env.template not found. Please create it first."
        exit 1
    fi
fi

# 7. Local Aider Config (Small & Specific)
echo "⚙️  Configuring Aider..."
cat <<EOF > .aider.conf.yml
model: mistral/devstral-2512
edit-format: whole
stream: true
map-tokens: 1024
EOF

echo "-------------------------------------------------------"
echo "🎉 SME AI Auditor Environment Setup Complete!"