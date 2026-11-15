FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./
COPY VERSION ./VERSION
COPY templates ./templates
COPY static ./static
RUN useradd --uid 10001 --create-home web && mkdir -p /data && chown web:web /data
USER web
EXPOSE 8000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]
