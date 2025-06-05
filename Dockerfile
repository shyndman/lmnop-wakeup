FROM ghcr.io/shyndman/lmnop-base:latest

# Copy the project into the intermediate image
ADD . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Expose the port the app runs on
EXPOSE 8002

# Add health check using the FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8000/health || exit 1

# Run the server subcommand
CMD ["/app/.venv/bin/wakeup", "server"]
