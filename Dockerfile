# 1) Temel imaj
FROM python:3.11-slim

# 2) Ortam değişkeni – apt interaktif olmadan çalışsın
ENV DEBIAN_FRONTEND=noninteractive

# 3) Sistem bağımlılıklarını yükle, TA-Lib kaynaktan derle ve temizle
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      wget \
      ca-certificates && \
    \
    # TA-Lib 0.4.0 kaynağını indir ve derle
    wget https://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib && \
      ./configure --prefix=/usr && \
      make && \
      make install && \
    cd .. && \
    \
    # Artefaktları sil
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz && \
    \
    # Artık gereksiz paketleri kaldır
    apt-get purge -y --auto-remove build-essential wget && \
    rm -rf /var/lib/apt/lists/*

# 4) Çalışma dizini
WORKDIR /app

# 5) Python bağımlılıklarını yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6) Proje dosyalarını kopyala
COPY . .

# 7) Konteyner başlatılınca main.py’i çalıştır
CMD ["python", "main.py"]
