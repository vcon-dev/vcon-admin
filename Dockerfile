# Stage 1: Build
FROM chainguard/python:latest-dev@sha256:e22e86b81a5ef8bf50ed6899e5d55ae44725791febde5a67bc2e8afd5939bad6 AS builder

# Set the working directory
WORKDIR /app

# Copy only the files necessary for dependency installation
COPY requirements.txt /app/
COPY custom_info.md /app/

# Install dependencies
USER root
RUN apk add --no-cache gcc
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM chainguard/python:latest@sha256:b69271bb5c3f06f5afa4c40a77867784e907408ab991e4d6e907f5aa796b87b8

# Set the working directory
WORKDIR /app

# Copy pre-installed dependencies from the builder stage
COPY --from=builder /app/ /app/

# Add application code
COPY . /app

# Update PATH to include dependencies
ENV PYTHONPATH="/app/dependencies:$PYTHONPATH"
ENV PATH="/app/dependencies/bin:$PATH"

# Expose necessary port
EXPOSE 8501

# Define default environment variable
ENV NAME World

# Run admin.py when the container launches
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
