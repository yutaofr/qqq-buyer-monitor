# v12.0 Operational Commands

> **The "Commands" - Environment & Scripts**

## MANDATE: Use Docker Environment
Never run `npm`, `pip`, `pytest`, or `python` directly on the host.

### 1. Production Inferencing
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.main
```

### 2. PIT-Compliant Performance Audit
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.backtest --evaluation-start 2010-01-01
```

### 3. Engine Unit Testing
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] pytest tests/unit/engine/v12 -q
```

### 4. Full Environment Validation
```bash
docker-compose up --build
```
