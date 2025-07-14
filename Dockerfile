# Use an official Ubuntu base image
FROM ubuntu:latest

# Set the working directory in the container
WORKDIR /app

# Install necessary packages
RUN apt-get update && \
    apt-get install -y software-properties-common curl && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    apt-get install -y python3.12 python3-pip python3.12-venv && \
    apt-get clean

# Install uv package manager using the official installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation and check where uv is installed
RUN find /root -name "uv" -type f 2>/dev/null || echo "uv not found in /root"
RUN ls -la /root/.local/bin/ 2>/dev/null || echo "/root/.local/bin/ not found"
RUN ls -la /root/.cargo/bin/ 2>/dev/null || echo "/root/.cargo/bin/ not found"

# Add possible uv locations to PATH
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv with explicit path search
RUN which uv && uv --version && uv sync

# Copy the current directory contents into the container
COPY . /app

# Run the command to start your bot
CMD ["uv", "run", "main.py"]

# To build the Docker image
# docker build -t your-image . (zeos-cat-ubuntu-02) (dont forget the dot)

# To run the Docker container with environment variables from a file
# docker run --env-file .env your-image
