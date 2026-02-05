FROM python:3.11-slim-bookworm

# Ustawienie kodowania dla polskich znaków i strefy czasowej
ENV PYTHONIOENCODING=utf-8
ENV TZ=Europe/Warsaw

WORKDIR /app

# Instalacja zależności systemowych dla psutil
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
