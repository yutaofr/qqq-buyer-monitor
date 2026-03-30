FROM python:3.13-slim

WORKDIR /app

# System deps for scipy/numpy compilation and data fetching
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Dummy src package so pip install -e . resolves correctly before COPY src
RUN mkdir -p src && touch src/__init__.py

RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

CMD ["python", "-m", "src.main"]
