FROM python:3.12-slim

# fonts-dejavu: písmo s diakritikou pre generovanie PDF (tools/generate_data.py)
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

ENV WORKSPACE=/workspace \
    INDEX_DIR=/index \
    PYTHONUNBUFFERED=1 \
    ANONYMIZED_TELEMETRY=False

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8501", \
     "--browser.gatherUsageStats=false", "--server.fileWatcherType=none"]
