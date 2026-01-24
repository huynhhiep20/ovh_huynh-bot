# Hướng dẫn chạy OVH Bot trên VPS với Docker

## Yêu cầu
- Docker và Docker Compose đã cài đặt trên VPS
- Token Telegram Bot và Chat ID

## Cách sử dụng

### 1. Clone repo và cấu hình
```bash
git clone <your-repo-url>
cd ovh_bot

# Tạo file .env với thông tin của bạn
cp env.example .env
nano .env
```

### 2. Cấu hình file .env
```bash
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
MODE=continuous
CHECK_INTERVAL=60
NOTIFY_ONLY_IN_STOCK=false
```

### 3. Build và chạy với Docker Compose
```bash
# Build và chạy
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng bot
docker-compose down

# Restart bot
docker-compose restart
```

### 4. Chạy với Docker thuần (không dùng compose)
```bash
# Build image
docker build -t ovh-bot .

# Chạy container
docker run -d \
  --name ovh-stock-checker \
  --restart unless-stopped \
  -e TELEGRAM_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  -e MODE=continuous \
  -e CHECK_INTERVAL=60 \
  ovh-bot

# Xem logs
docker logs -f ovh-stock-checker

# Dừng container
docker stop ovh-stock-checker

# Xóa container
docker rm ovh-stock-checker
```

## Quản lý trên VPS

### Kiểm tra trạng thái
```bash
docker ps
docker-compose ps
```

### Xem logs
```bash
# Xem logs realtime
docker-compose logs -f

# Xem 100 dòng logs cuối
docker-compose logs --tail=100

# Xem logs từ 1 giờ trước
docker-compose logs --since 1h
```

### Update code mới
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Troubleshooting

#### Bot không chạy
```bash
# Kiểm tra logs để xem lỗi
docker-compose logs

# Kiểm tra biến môi trường
docker-compose config
```

#### Thiếu bộ nhớ
Chỉnh giới hạn trong `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # Giảm xuống nếu VPS yếu
```

#### Chạy một lần để test
```bash
docker-compose run --rm ovh-bot python check_vps.py
```

## Auto-start khi VPS reboot

Docker đã được cấu hình `restart: unless-stopped`, bot sẽ tự động chạy lại khi VPS khởi động.

Để chắc chắn Docker service tự động start:
```bash
sudo systemctl enable docker
```

## Monitoring

### Kiểm tra tài nguyên đang dùng
```bash
docker stats ovh-stock-checker
```

### Backup logs
```bash
docker-compose logs > backup-logs-$(date +%Y%m%d).txt
```
