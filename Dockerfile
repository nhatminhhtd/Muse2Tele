# Muse2Tele tren Render — ban da sua cho Linux/container.
# KHONG dung mau goc: repo khong co main.py o root, va bot/FoxProfile ban Windows
# khong chay thang tren Linux. Xem run_bot_linux.py + start.sh.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Deps cho Tailscale + Camoufox (Firefox) + Xvfb (headless "virtual").
# python:3.10-slim trong mau goc thieu cac thu vien nay nen trinh duyet se khong mo duoc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates procps tini xvfb \
    libgtk-3-0 libasound2 libdbus-glib-1-2 libxt6 libx11-xcb1 libdrm2 libgbm1 \
    libnss3 libatk-bridge2.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxrandr2 libpango-1.0-0 libcairo2 fonts-liberation \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cai dependencies truoc de tan dung cache layer. requirements.txt goc co dong
# "-r foxprofile/repo/requirements.txt" nen phai copy ca 2 file truoc khi pip install.
COPY requirements.txt ./
COPY foxprofile/repo/requirements.txt ./foxprofile/repo/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && python -m camoufox fetch

# Copy toan bo source. .dockerignore se loai .env, foxprofile/data, state, log.
COPY . .
RUN chmod +x start.sh

# tini lam PID 1 de SIGTERM cua Render toi duoc tien trinh chinh khi restart/stop.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["./start.sh"]
