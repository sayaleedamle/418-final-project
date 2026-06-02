# Build context: final_project/final_project/
# docker build -f streamlit_app/Dockerfile -t truthcheck-streamlit .
# docker run -p 8501:8501 -e API_URL=https://your-api.run.app truthcheck-streamlit

FROM python:3.11-slim

WORKDIR /app

COPY streamlit_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streamlit_app/app.py app.py

# API_URL is overridden at runtime to point at the deployed Flask API
ENV API_URL="http://localhost:8080"

EXPOSE 8501

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
