# Build context: final_project/final_project/
# docker build -f api/Dockerfile -t truthcheck-api .

FROM python:3.11-slim

WORKDIR /app

# Install the truthcheck package and its dependencies first
# (separate layer so this is cached on code-only changes)
COPY pyproject.toml .
COPY truthcheck/ truthcheck/
RUN pip install --no-cache-dir .

# Install Flask API dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the API entrypoint to the working directory root
COPY api/app.py app.py

EXPOSE 8080

# 2 workers; 300 s timeout for long fact-check requests
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "300", "app:app"]
