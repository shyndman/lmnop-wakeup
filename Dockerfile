# Install uv
FROM python:3.13-slim AS builder

# Change the working directory to the `app` directory
WORKDIR /app

RUN apt update && apt install -y --no-install-recommends \
    curl ca-certificates wget curl nala

RUN nala fetch --auto --assume-yes --country CA --debian bookworm

# The installer requires curl (and certificates) to download the release archive
RUN nala update && nala install -y --no-install-recommends \
      git libavcodec-extra ffmpeg

RUN rm -rf /var/lib/apt/lists/*

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy the project into the intermediate image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# FROM python:3.13-slim

# # Copy the environment, but not the source code
# COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Expose the port the app runs on
EXPOSE 8000

# Add health check using the FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# Run the server subcommand
CMD ["/app/.venv/bin/wakeup", "server"]
