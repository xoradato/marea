# Marea in a container. The AMD Token Factory key is passed at run time, never baked into the image:
#   docker build -t marea .
#   docker run -p 8501:8501 --env-file .env marea
# Without the AMD_* variables the app still runs, on offline templates.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
