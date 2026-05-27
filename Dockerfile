FROM python:3.12-slim

# Gerekli sistem paketlerini (ffmpeg ve derleme araçları) yükle
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm kodları kopyala
COPY . .

# Web paneli (dashboard) için portu dışarı aç
EXPOSE 5000

# Botu çalıştır
CMD ["python", "bot.py"]
