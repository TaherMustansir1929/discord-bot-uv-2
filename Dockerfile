# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user first
RUN useradd --create-home --shell /bin/bash app

# Install uv package manager globally so it's accessible to all users
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/uv && \
    cp /root/.local/bin/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx

# Verify uv installation
RUN uv --version

# Set working directory
WORKDIR /app

# Copy entrypoint script
COPY <<EOF /app/entrypoint.sh
#!/bin/bash
set -e

echo "Pulling code from GitHub repository..."

# Validate that GITHUB_REPO is set
if [ -z "\$GITHUB_REPO" ]; then
    echo "Error: GITHUB_REPO environment variable is required"
    echo "Example: GITHUB_REPO=https://github.com/username/discord-bot-repo.git"
    exit 1
fi

# Clone or pull the repository
if [ -d "/app/bot-code/.git" ]; then
    echo "Updating existing repository..."
    cd /app/bot-code
    git fetch origin
    git reset --hard origin/\${GITHUB_BRANCH}
else
    echo "Cloning repository..."
    git clone https://github.com/TaherMustansir1929/discord-bot-uv-2.git /app/bot-code
fi

cd /app/bot-code

# Check if pyproject.toml exists (for uv)
if [ -f "pyproject.toml" ]; then
    echo "Installing dependencies with uv using pyproject.toml..."
    uv sync
    echo "Starting Discord bot with uv..."
    uv run main.py
elif [ -f "requirements.txt" ]; then
    echo "Installing dependencies with uv using requirements.txt..."
    uv pip install -r requirements.txt
    echo "Starting Discord bot..."
    python main.py
else
    echo "No pyproject.toml or requirements.txt found. Attempting to run main.py directly..."
    python main.py
fi
EOF

# Make entrypoint script executable and fix ownership
RUN chmod +x /app/entrypoint.sh && \
    chown -R app:app /app

# Set up environment variables for the GitHub repository
ENV GITHUB_REPO="https://github.com/TaherMustansir1929/discord-bot-uv-2.git"
ENV GITHUB_BRANCH="main"

# Switch to non-root user
USER app

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]