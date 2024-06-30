# Stage 1: Build dependencies and install Python packages
FROM python:3.10-alpine as builder

# Set the working directory
WORKDIR /app

# Install dependencies for Python and build tools
RUN apk add --no-cache \
    python3-dev \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    git \
    build-base

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python3 -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip wheel && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /app/venv/bin/pip uninstall -y discord py-cord && \
    /app/venv/bin/pip install --no-cache-dir discord py-cord && \
    /app/venv/bin/pip uninstall -y discord

# Stage 2: Final runtime image
FROM python:3.10-alpine

# Set the working directory
WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache python3 libstdc++ libffi openssl

# Copy the virtual environment from the builder
COPY --from=builder /app/venv /app/venv

# Copy the application source code
COPY . .

# Activate virtual environment for the container runtime
ENV PATH="/app/venv/bin:$PATH"

# Expose the Flask port
EXPOSE 5000

# Ensure the start.sh script is executable
RUN chmod +x start.sh

# Set the entry point to the start.sh script
ENTRYPOINT ["./start.sh"]
