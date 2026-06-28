# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir --quiet pytest

# Default command runs the demo over data/leads.json. Override:
#   docker run --rm <image> python cli.py data/leads-real-estate.json
#   docker run --rm <image> python cli.py data/leads.json --no-dedupe
#   docker run --rm <image> python evals/run.py
#   docker run --rm <image> python -m pytest -q
CMD ["python", "run.py"]
