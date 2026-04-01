# v12.1 Operational Commands

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

### 3. WFO Parameter Optimization
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m scripts.run_v12_wfo
```

### 4. Mathematical Falsification (White-noise Test)
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python scripts/falsify_sentinel_white_noise.py
```

### 5. Full Environment Validation
```bash
docker-compose up --build
```
