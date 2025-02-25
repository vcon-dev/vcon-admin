# ------------------------------------------------------------------------------
# Stage 1: Build
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app
USER root

# Install build dependencies including Rust
RUN apt-get update && apt-get install -y \
    gcc make git curl bash && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y

# Add Cargo to PATH (avoid using source)
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Verify Rust installation 
RUN bash -c "cargo --version"

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/usr/local python3 -

# Copy your project files for the build
COPY pyproject.toml poetry.lock* /app/
COPY custom_info.md /app/

# Install all dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction

# ------------------------------------------------------------------------------
# Stage 2: Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

# Copy installed site-packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy your actual application code
COPY . /app

# Expose a server port (e.g. if using Streamlit)
EXPOSE 8501

# Run your app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
