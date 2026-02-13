FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install dependencies (frozen = use existing lock file)
RUN uv sync --no-dev --frozen

# Run the bot
CMD ["uv", "run", "python", "-m", "d_brain"]
