import requests
import os
import time
from datetime import datetime
import re

# Load environment variables from .env file (if exists)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium không khả dụng")
    print("💡 Cài: pip install selenium webdriver-manager")

# Cấu hình từ biến môi trường (GitHub Secrets hoặc .env)
# Không hardcode token/chat_id – bắt buộc set env để tránh lộ secret
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Mode: once hoặc continuous
MODE = os.environ.get('MODE', 'continuous')

# Chỉ thông báo khi có hàng (mặc định: false = báo cả hết hàng và có hàng)
NOTIFY_ONLY_IN_STOCK = os.environ.get('NOTIFY_ONLY_IN_STOCK', 'false').lower() == 'true'

# Cấu hình thời gian kiểm tra (giây)
def _parse_check_interval():
    val = os.environ.get('CHECK_INTERVAL', '60')
    try:
        n = int(val)
        return max(30, n) if n > 0 else 60
    except (ValueError, TypeError):
        return 60


CHECK_INTERVAL = _parse_check_interval()


def send_telegram(message):
    """Gửi thông báo qua Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Chưa cấu hình TELEGRAM_TOKEN / TELEGRAM_CHAT_ID (set env)")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Đã gửi thông báo Telegram")
        else:
            print(f"❌ Lỗi gửi Telegram: {response.status_code}")
    except Exception as e:
        print(f"❌ Lỗi kết nối Telegram: {e}")


def fetch_ovh_configurator_with_asia_tab(url, timeout=30):
    """
    Mở trang OVH configurator, click vào tab Asia/Oceania, và lấy HTML
    
    Args:
        url: URL trang configurator
        timeout: Timeout giây
    
    Returns:
        str: HTML content sau khi click vào Asia tab
    """
    if not SELENIUM_AVAILABLE:
        raise Exception("Selenium không khả dụng")
    
    # Cấu hình Chrome headless
    chrome_options = ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = None
    try:
        # Trên GitHub Actions/Ubuntu: dùng chromedriver từ system (đã cài qua apt)
        # Local: webdriver-manager sẽ tự động tải
        try:
            # Thử dùng system chromedriver trước (cho GitHub Actions)
            service = ChromeService('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            # Fallback: dùng webdriver-manager (cho local)
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.set_page_load_timeout(timeout)
        
        print("🌐 Đang mở trang OVH configurator...")
        driver.get(url)
        
        # Đợi trang load
        time.sleep(3)
        
        # Đóng cookie consent / privacy popup nếu có
        print("🍪 Kiểm tra cookie popup...")
        try:
            # OVH sử dụng cookie banner với ID cụ thể
            cookie_selectors = [
                '#header_tc_privacy_button_3',  # Accept button của OVH
                '#header_tc_privacy_button',     # Continue without accepting
                'button[data-tc-privacy="cookie-banner::accept"]',  # Data attribute
                '#didomi-notice-agree-button',
                'button[id*="accept"]',
                'button[id*="cookie"]',
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_btn.is_displayed():
                        cookie_btn.click()
                        print(f"✅ Đã đóng cookie popup ({selector})")
                        time.sleep(2)  # Đợi DOM stable sau khi đóng popup
                        break
                except:
                    continue
        except Exception as e:
            print(f"⚠️  Không có cookie popup")
        
        # Tìm và click vào tab Asia-Pacific (retry nếu bị revert)
        print("🔍 Tìm và click tab Asia/Oceania...")
        
        max_click_retries = 3
        tab_activated = False
        
        for click_attempt in range(max_click_retries):
            try:
                # Đợi tab xuất hiện
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-value="Asia-Pacific"]'))
                )
                
                # Dùng JavaScript click + trigger events đầy đủ
                click_result = driver.execute_script("""
                    const tab = document.querySelector('button[data-value="Asia-Pacific"]');
                    if (tab) {
                        tab.scrollIntoView({behavior: 'smooth', block: 'center'});
                        tab.focus();
                        
                        // Trigger mousedown, mouseup, click events
                        ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                            const event = new MouseEvent(eventType, {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            });
                            tab.dispatchEvent(event);
                        });
                        
                        tab.click();
                        
                        return {
                            text: tab.textContent,
                            disabled: tab.disabled,
                            ariaSelected: tab.getAttribute('aria-selected')
                        };
                    }
                    return null;
                """)
                
                if click_result:
                    print(f"   ✅ Click lần {click_attempt + 1}: {click_result['text'].strip()}")
                    
                    # Đợi 2s để tab stable
                    time.sleep(2)
                    
                    # Verify tab vẫn còn active
                    tab_still_active = driver.execute_script("""
                        const tab = document.querySelector('button[data-value="Asia-Pacific"]');
                        return tab ? tab.getAttribute('aria-selected') === 'true' : false;
                    """)
                    
                    if tab_still_active:
                        print(f"   ✅ Tab Asia vẫn active sau 2s")
                        tab_activated = True
                        break
                    else:
                        print(f"   ⚠️  Tab bị revert về cũ, thử click lại...")
                        time.sleep(1)
                else:
                    print("⚠️  Không tìm thấy tab Asia/Oceania")
                    raise Exception("Tab Asia/Oceania not found")
                    
            except Exception as e:
                print(f"   ❌ Lỗi click lần {click_attempt + 1}: {e}")
                if click_attempt == max_click_retries - 1:
                    raise
                time.sleep(1)
        
        if not tab_activated:
            print("❌ Tab Asia không thể activate sau 3 lần thử")
            print("💡 OVH có thể block hoặc tab bị validation check")
            raise Exception("Cannot activate Asia tab")
        
        # Đợi content load
        print("⏳ Đang đợi tab content load...")
        time.sleep(2)
        
        # Retry check cho datacenter Asia load
        max_retries = 5
        content_found = False
        
        for attempt in range(max_retries):
            asia_dcs = driver.execute_script("""
                const buttons = document.querySelectorAll('[class*="_button"]');
                const asiaCodes = [];
                for (let btn of buttons) {
                    const match = btn.className.match(/([A-Z]{2,4})_button/);
                    if (match) {
                        const code = match[1];
                        if (['YNM', 'SGP', 'SYD', 'TYO', 'SEL', 'HKG'].includes(code)) {
                            asiaCodes.push(code);
                        }
                    }
                }
                return asiaCodes.length > 0 ? asiaCodes : null;
            """)
            
            if asia_dcs:
                print(f"✅ Đã load nội dung Asia (tìm thấy: {', '.join(asia_dcs)})")
                content_found = True
                break
            else:
                print(f"⏳ Chờ content load... (lần {attempt + 1}/{max_retries})")
                time.sleep(2)
        
        if not content_found:
            print("⚠️  Tab content có thể chưa load hoặc không có datacenter Asia")
        
        # Lấy HTML sau khi load
        html_content = driver.page_source
        return html_content
        
    except Exception as e:
        print(f"❌ Lỗi browser automation: {e}")
        raise
    finally:
        if driver:
            driver.quit()


def parse_ovh_configurator_datacenters(html_content):
    """
    Parse HTML từ OVH configurator để lấy danh sách datacenter Asia
    
    Args:
        html_content: HTML sau khi click vào Asia tab
    
    Returns:
        list: [{'name': str, 'code': str, 'available': bool}, ...]
    """
    datacenters = []
    
    # Tìm tất cả XXX_button trong HTML
    button_pattern = r'class="([A-Z]{2,4})_button[^"]*"'
    button_matches = re.findall(button_pattern, html_content)
    
    # Filter chỉ lấy Asia datacenter codes
    asia_codes = ['YNM', 'SGP', 'SYD', 'TYO', 'SEL', 'HKG', 'SIN', 'BOM']
    
    print(f"🔍 Tìm thấy {len(button_matches)} datacenter buttons: {', '.join(set(button_matches))}")
    
    # Tìm TẤT CẢ role="radio" với position để parse theo thứ tự
    radio_pattern = r'<div role="radio"[^>]*aria-disabled="([^"]*)"[^>]*aria-labelledby="[^"]*"[^>]*class="([A-Z]{2,4})_button'
    all_radios = []
    
    for match in re.finditer(radio_pattern, html_content):
        aria_disabled = match.group(1)
        code = match.group(2)
        start_pos = match.start()
        
        if code not in asia_codes:
            continue
        
        # Tìm ending position (next role="radio" hoặc end of content)
        next_radio = re.search(r'<div role="radio"', html_content[start_pos + 100:])
        if next_radio:
            end_pos = start_pos + 100 + next_radio.start()
        else:
            end_pos = len(html_content)
        
        content = html_content[start_pos:end_pos]
        
        # Extract name từ <h5> tag
        name_match = re.search(r'<h5[^>]*>([^<]+)</h5>', content)
        dc_name = name_match.group(1).strip() if name_match else code
        
        # Check availability
        has_available = 'Available now' in content
        has_out_of_stock = 'Out of stock' in content
        is_disabled = aria_disabled == "true"
        
        # CÓ HÀNG nếu: có "Available now" VÀ không có "Out of stock" VÀ không disabled
        available = has_available and not has_out_of_stock and not is_disabled
        
        datacenters.append({
            'name': dc_name,
            'code': code,
            'available': available
        })
        
        # Debug log
        status_icon = "✅" if available else "❌"
        print(f"   {status_icon} {code}: disabled={is_disabled}, out_of_stock={has_out_of_stock}, available={has_available}")
    
    return datacenters




def format_stock_status(regions_status):
    """
    Format thông báo trạng thái hàng
    
    Args:
        regions_status: List of dict với keys: name, available, found
    
    Returns:
        tuple: (has_stock: bool, message: str)
    """
    has_any_stock = False
    messages = []
    
    for region in regions_status:
        if region['available']:
            messages.append(f"✅ {region['name']}: CÓ HÀNG!")
            has_any_stock = True
        else:
            messages.append(f"❌ {region['name']}: Hết hàng")
    
    if not messages:
        return False, "⚠️ Không tìm thấy thông tin datacenter"
    
    return has_any_stock, '\n'.join(messages)


def check_stock():
    """Kiểm tra tình trạng còn hàng của VPS OVH cho khu vực Asia"""
    if not SELENIUM_AVAILABLE:
        print("\n❌ Selenium chưa cài đặt hoặc không khả dụng")
        print("💡 Cài: pip install selenium webdriver-manager")
        print("💡 Cài Chrome: brew install --cask google-chrome (macOS)")
        return
    
    configurator_url = "https://www.ovhcloud.com/en/vps/configurator/?planCode=vps-2025-model1"

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{current_time}] 🔍 Đang kiểm tra tình trạng VPS khu vực Asia...")
        
        # Lấy HTML sau khi click vào Asia tab
        html_content = fetch_ovh_configurator_with_asia_tab(configurator_url)
        print(f"📄 Kích thước response: {len(html_content)} ký tự")
        
        # Parse datacenters từ configurator
        datacenters = parse_ovh_configurator_datacenters(html_content)
        
        if not datacenters:
            print("\n⚠️  Không tìm thấy datacenter Asia trong tab")
            print("💡 Tab Asia/Oceania có thể trống hoặc HTML structure thay đổi")
            print("💡 Kiểm tra file /tmp/ovh_asia_tab.html để debug")
            # Lưu HTML để debug
            try:
                with open('/tmp/ovh_asia_tab.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("💾 Đã lưu HTML vào /tmp/ovh_asia_tab.html")
            except:
                pass
            return
        
        print(f"\n🌏 Tìm thấy {len(datacenters)} datacenter Asia:")
        all_results = []
        has_available = False
        
        for dc in datacenters:
            status_icon = "✅" if dc['available'] else "❌"
            status_text = "CÓ HÀNG" if dc['available'] else "Hết hàng"
            print(f"   {status_icon} {dc['name']} [{dc['code']}]: {status_text}")
            
            if dc['available']:
                has_available = True
            
            all_results.append({
                'name': dc['name'],
                'available': dc['available'],
                'found': True
            })
        
        # Tổng hợp kết quả
        has_stock, status_message = format_stock_status(all_results)
        
        print(f"\n📊 KẾT QUẢ TỔNG HỢP:")
        print(status_message)
        
        # Gửi Telegram theo cấu hình
        if has_stock:
            # CÓ HÀNG - luôn gửi
            telegram_message = f"🔥 VPS OVH KHU VỰC ASIA CÓ HÀNG!\n\n{status_message}\n\nLink: {configurator_url}\n\n⚡ Nhanh tay đặt hàng!"
            send_telegram(telegram_message)
        else:
            # HẾT HÀNG - gửi nếu NOTIFY_ONLY_IN_STOCK = false
            if not NOTIFY_ONLY_IN_STOCK:
                telegram_message = f"📭 VPS OVH Khu vực Asia\n\n{status_message}\n\nLink: {configurator_url}"
                send_telegram(telegram_message)
                print("\n📭 Đã gửi thông báo hết hàng qua Telegram")
            else:
                print("\n📭 Tất cả datacenter đều hết hàng (không gửi Telegram vì NOTIFY_ONLY_IN_STOCK=true)")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


def run_continuous():
    """Chạy liên tục với interval được cấu hình"""
    print("=" * 70)
    print("🤖 OVH VPS Stock Checker - Giám sát khu vực Asia")
    print("=" * 70)
    print(f"⏰ Kiểm tra mỗi {CHECK_INTERVAL} giây")
    print(f"🌏 Khu vực: Singapore, Mumbai, Sydney, Tokyo, Seoul")
    print(f"📱 Telegram: {'Đã cấu hình' if (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID) else 'Chưa cấu hình'}")
    print(f"🔔 Chế độ thông báo: {'Chỉ khi có hàng' if NOTIFY_ONLY_IN_STOCK else 'Cả có hàng và hết hàng'}")
    print(f"🔔 Bấm Ctrl+C để dừng")
    print("=" * 70)
    
    check_count = 0
    try:
        while True:
            check_count += 1
            print(f"\n{'='*70}")
            print(f"📊 Lần kiểm tra thứ {check_count}")
            print(f"{'='*70}")
            check_stock()
            
            print(f"\n⏳ Đợi {CHECK_INTERVAL} giây cho lần kiểm tra tiếp theo...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"🛑 Đã dừng chương trình")
        print(f"📈 Tổng số lần kiểm tra: {check_count}")
        print(f"{'='*70}")


if __name__ == "__main__":
    # Kiểm tra nếu chạy một lần hay liên tục
    mode = os.environ.get('MODE', 'continuous').lower()
    
    if mode == 'once':
        # Chạy một lần (cho GitHub Actions)
        check_stock()
    else:
        # Chạy liên tục (cho local testing)
        run_continuous()