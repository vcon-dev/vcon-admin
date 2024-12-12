# Stage 1: Build
FROM cgr.dev/chainguard/python:latest-dev AS builder

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
FROM cgr.dev/chainguard/python:latest

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
