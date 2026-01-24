# Sử dụng Python image với Chrome đã cài sẵn
FROM python:3.12-slim

# Cài đặt Chrome và các dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Copy requirements và cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Thiết lập biến môi trường mặc định
ENV MODE=continuous \
    CHECK_INTERVAL=60 \
    NOTIFY_ONLY_IN_STOCK=false \
    PYTHONUNBUFFERED=1

# Chạy bot
CMD ["python", "check_vps.py"]
