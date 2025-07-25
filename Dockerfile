# Use an appropriate Python base image
FROM python:3.12-slim

# Set a working directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy pyproject.toml and uv.lock (if it exists)
COPY pyproject.toml uv.lock* ./

# Install project dependencies using uv
# Use --frozen-lockfile if uv.lock is present and should be strictly followed
# Otherwise, fall back to installing from pyproject.toml
# This assumes uv.lock is generated and committed if used.
RUN if [ -f uv.lock ]; then \
    uv sync --frozen; \
    else \
    uv pip install .; \
    fi

# Copy the entire project content into the working directory
# Ensure .env itself is NOT copied (this should be handled by .dockerignore and build context)
COPY src/ ./src/
COPY .env.example ./.env.example
COPY main.py ./main.py
COPY README.md ./README.md
COPY docs/ ./docs/

# Set PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Create directory for persistent data storage
RUN mkdir -p /app/data && chmod 755 /app/data

# Expose the port Streamlit runs on
EXPOSE 8501

# Set the CMD to run the Streamlit application
CMD ["uv", "run", "streamlit", "run", "src/inventree_order_calculator/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]