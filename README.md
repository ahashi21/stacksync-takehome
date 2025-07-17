# Python Code Execution Service

A secure API service for executing Python scripts with built-in safety measures and resource limits.

## Overview

This service accepts Python scripts via HTTP POST requests and executes them in a controlled environment. All scripts must contain a `main()` function that returns JSON-serializable data.

Note: While this implementation was originally designed to use nsjail for sandboxing, Google Cloud Run’s security model prohibits the privileged syscalls and namespace operations required by nsjail. As a fallback, the service applies a combination of AST-based script validation, process-level isolation, and resource limits to ensure safe execution of untrusted Python code when nsjail is unavailable.

## API

### POST /execute

Execute a Python script.

Request:
```json
{
  "script": "def main():\n    return {'result': 42}"
}
```

Response:
```json
{
  "result": {"result": 42},
  "stdout": ""
}
```

### GET /health

Health check endpoint.

## Local Usage

Build and run:
```bash
docker build -t python-executor .
docker run -p 8080:8080 python-executor
```

Test:
```bash
curl -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"script": "def main():\n    return {\"hello\": \"world\"}"}'
```

## Requirements

Scripts must:
- Contain a `main()` function
- Return JSON-serializable data
- Use only allowed imports (os, pandas, numpy, standard library)

## Available Libraries

- os
- pandas
- numpy  
- Standard Python library (json, math, datetime, etc.)

## Security

- AST validation blocks dangerous imports and functions
- Resource limits prevent abuse (CPU, memory, time)
- Process isolation in temporary directories
- 30-second execution timeout

## Examples

Basic usage:
```python
def main():
    return {"message": "Hello World"}
```

With pandas:
```python
def main():
    import pandas as pd
    df = pd.DataFrame({"x": [1, 2, 3]})
    return {"mean": df["x"].mean()}
```