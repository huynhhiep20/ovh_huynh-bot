# OVH VPS Stock Checker - Giám sát khu vực Asia

Bot tự động kiểm tra VPS OVH có hàng ở datacenter Asia/Oceania (Singapore, Mumbai, Sydney, Tokyo, Seoul) và gửi thông báo qua Telegram.

## Cách hoạt động

1. Mở trang [OVH VPS Configurator](https://www.ovhcloud.com/en/vps/configurator/) bằng Selenium
2. Click vào tab **"Asia/Oceania"** để hiển thị datacenter khu vực này
3. Parse HTML để lấy danh sách datacenter và status (available/out of stock)
4. Gửi Telegram khi phát hiện có hàng

## Tính năng

- ✅ Kiểm tra real-time từ trang OVH chính thức
- 📱 Gửi thông báo Telegram khi có hàng
- 🌏 Hỗ trợ datacenter: Singapore, Mumbai, Sydney, Tokyo, Seoul
- 🚀 Chạy trên GitHub Actions (mỗi 10 phút) hoặc local
- 🤖 Tự động cài ChromeDriver

## Cài đặt

### 1. Dependencies

```bash
pip install -r requirements.txt
```

### 2. Chrome/Chromium (bắt buộc)

**macOS:**
```bash
brew install --cask google-chrome
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

**Docker:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y chromium chromium-driver
```

> **Lưu ý:** Selenium cần Chrome/Chromium để hoạt động. GitHub Actions runner đã có sẵn.

## Cấu hình

### 1. Biến môi trường

Copy `env.example` thành `.env` và điền giá trị:

```bash
# Bắt buộc để gửi Telegram
TELEGRAM_TOKEN=your_bot_token_from_@BotFather
TELEGRAM_CHAT_ID=your_chat_id

# Tùy chọn
MODE=continuous              # continuous (local loop) | once (GitHub Actions)
CHECK_INTERVAL=60            # Kiểm tra mỗi 60 giây (tối thiểu 30)
NOTIFY_ONLY_IN_STOCK=false   # true = chỉ báo có hàng | false = báo cả có và hết hàng
```

### 2. Lấy Telegram credentials

1. **Tạo bot:** Chat với [@BotFather](https://t.me/BotFather) → `/newbot` → lấy `TELEGRAM_TOKEN`
2. **Lấy chat ID:** Chat với [@userinfobot](https://t.me/userinfobot) → lấy `TELEGRAM_CHAT_ID`

### 3. GitHub Secrets (cho Actions)

Vào repo → Settings → Secrets and variables → Actions → New repository secret:
- `TELEGRAM_TOKEN`: Token từ BotFather
- `TELEGRAM_CHAT_ID`: Chat ID của bạn

## Sử dụng

### Chạy local

```bash
# Cài dependencies
pip install -r requirements.txt

# Chạy liên tục (kiểm tra mỗi 60s) - báo cả hết hàng và có hàng
TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python3 check_vps.py

# Chạy một lần
MODE=once TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python3 check_vps.py

# Chỉ báo khi có hàng (sau khi test ổn định)
NOTIFY_ONLY_IN_STOCK=true TELEGRAM_TOKEN=xxx TELEGRAM_CHAT_ID=yyy python3 check_vps.py
```

**Lưu ý về NOTIFY_ONLY_IN_STOCK:**
- Mặc định (`false`): Bot báo cả khi hết hàng và có hàng - giúp bạn biết bot đang hoạt động
- Set `true`: Bot chỉ báo khi có hàng - dùng khi bot đã chạy ổn định để tránh spam

### Test Selenium (debug)

```bash
python3 test_selenium.py
```

Script này sẽ:
- Mở Chrome và navigate đến OVH configurator
- Click tab "Asia/Oceania"
- In ra datacenter tìm thấy
- Lưu HTML vào `/tmp/ovh_asia_tab.html`

### GitHub Actions

- **Tự động:** Chạy mỗi 10 phút (cron: `*/10 * * * *`)
- **Thủ công:** Actions → OVH Stock Checker → Run workflow

## Kết quả mẫu

```
[2026-01-24 12:00:00] 🔍 Đang kiểm tra tình trạng VPS khu vực Asia...
🌐 Đang mở trang OVH configurator...
🔍 Tìm tab Asia/Oceania...
✅ Tìm thấy tab Asia/Oceania, đang click...
✅ Đã load nội dung Asia
📄 Kích thước response: 523041 ký tự

🌏 Tìm thấy 2 datacenter Asia:
   ✅ Singapore: CÓ HÀNG!
   ❌ Mumbai: Hết hàng

📊 KẾT QUẢ TỔNG HỢP:
✅ Singapore: CÓ HÀNG!
❌ Mumbai: Hết hàng

✅ Đã gửi thông báo Telegram
```

## Troubleshooting

**Q: Lỗi "Selenium không khả dụng"?**  
A: Chạy `pip install selenium webdriver-manager`

**Q: Lỗi Chrome/ChromeDriver?**  
A: Cài Chrome theo hướng dẫn phần "Cài đặt" ở trên. `webdriver-manager` sẽ tự động tải ChromeDriver.

**Q: Tab Asia/Oceania trống?**  
A: OVH có thể chưa mở bán VPS ở khu vực này. Chạy `test_selenium.py` để xem HTML thực tế.

**Q: Muốn check thêm khu vực khác?**  
A: Sửa `asia_keywords` trong `parse_ovh_configurator_datacenters()` (file `check_vps.py`)

## Cấu trúc project

```
ovh_bot/
├── check_vps.py          # Main script
├── test_selenium.py      # Test script (debug)
├── requirements.txt      # Dependencies
├── env.example           # Environment variables template
├── README.md
└── .github/workflows/
    └── main.yml          # GitHub Actions workflow
```

## License

MIT
