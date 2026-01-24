#!/usr/bin/env python3
"""
Script test Selenium để kiểm tra tab Asia/Oceania trên OVH Configurator
Chạy: python3 test_selenium.py
"""

import sys
import time
import re

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(f"❌ Import lỗi: {e}")
    print("\n💡 Cài dependencies:")
    print("   pip install selenium webdriver-manager")
    sys.exit(1)

def test_ovh_asia_tab():
    url = "https://www.ovhcloud.com/en/vps/configurator/?planCode=vps-2025-model1"
    
    chrome_options = ChromeOptions()
    # Comment dòng dưới để xem browser (không headless)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        print("🚀 Khởi động Chrome...")
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        print(f"🌐 Mở trang: {url}")
        driver.get(url)
        
        print("⏳ Đợi 3 giây để trang load...")
        time.sleep(3)
        
        # Đóng cookie popup nếu có
        print("🍪 Kiểm tra cookie popup...")
        try:
            cookie_selectors = [
                '#header_tc_privacy_button_3',  # OVH Accept button
                '#header_tc_privacy_button',     # Continue without accepting
                'button[data-tc-privacy="cookie-banner::accept"]',
                '#didomi-notice-agree-button',
                'button[id*="accept"]',
                'button[id*="cookie"]',
            ]
            for selector in cookie_selectors:
                try:
                    cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if cookie_btn.is_displayed():
                        cookie_btn.click()
                        print(f"✅ Đã đóng cookie popup: {selector}")
                        time.sleep(2)  # Đợi DOM stable
                        break
                except:
                    continue
        except:
            pass
        
        # Tìm và click tab Asia/Oceania (retry nếu bị revert)
        print("🔍 Tìm và click tab Asia/Oceania...")
        
        max_click_retries = 3
        tab_activated = False
        
        for click_attempt in range(max_click_retries):
            try:
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
                    
                    # Đợi 2s
                    time.sleep(2)
                    
                    # Verify tab vẫn active
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
                    print("❌ Không tìm thấy tab")
                    return False
                    
            except Exception as e:
                print(f"   ❌ Lỗi click lần {click_attempt + 1}: {str(e)[:100]}")
                if click_attempt == max_click_retries - 1:
                    raise
                time.sleep(1)
        
        if not tab_activated:
            print("❌ Tab không thể giữ trạng thái active")
            print("💡 OVH có thể có validation hoặc tab bị auto-revert")
            return False
        
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
                print(f"✅ Đã load datacenter Asia: {', '.join(asia_dcs)}")
                content_found = True
                break
            else:
                print(f"   ⏳ Chờ content load... (lần {attempt + 1}/{max_retries})")
                time.sleep(2)
        
        if not content_found:
            print("⚠️  Không tìm thấy datacenter Asia sau 10s")
        
        # Lấy HTML sau khi click
        html = driver.page_source
        
        # Parse datacenter từ HTML (use finditer to preserve order)
        print("\n🔎 Parse datacenter từ HTML:")
        
        # Tìm ALL role="radio" với XXX_button
        radio_pattern = r'<div role="radio"[^>]*aria-disabled="([^"]*)"[^>]*aria-labelledby="[^"]*"[^>]*class="([A-Z]{2,4})_button'
        
        asia_codes = ['YNM', 'SGP', 'SYD', 'TYO', 'SEL', 'HKG', 'SIN', 'BOM']
        asia_dcs = []
        
        for match in re.finditer(radio_pattern, html):
            aria_disabled = match.group(1)
            code = match.group(2)
            start_pos = match.start()
            
            if code not in asia_codes:
                continue
            
            # Find end position (next role="radio")
            next_radio = re.search(r'<div role="radio"', html[start_pos + 100:])
            end_pos = start_pos + 100 + next_radio.start() if next_radio else len(html)
            
            content = html[start_pos:end_pos]
            
            # Extract name
            name_match = re.search(r'<h5[^>]*>([^<]+)</h5>', content)
            name = name_match.group(1).strip() if name_match else code
            
            # Check availability
            has_available = 'Available now' in content
            has_out_of_stock = 'Out of stock' in content
            is_disabled = aria_disabled == "true"
            
            available = has_available and not has_out_of_stock and not is_disabled
            
            asia_dcs.append({
                'name': name,
                'code': code,
                'available': available
            })
            
            if available:
                print(f"   ✅ {name} [{code}]: CÓ HÀNG")
            else:
                print(f"   ❌ {name} [{code}]: Hết hàng")
        
        print(f"\nℹ️  Tổng cộng: {len(asia_dcs)} datacenter Asia")
        
        # === KẾT QUẢ CUỐI CÙNG ===
        print("\n" + "="*50)
        if any(dc['available'] for dc in asia_dcs):
            print("🎉 KẾT QUẢ: CÓ HÀNG!")
            for dc in asia_dcs:
                if dc['available']:
                    print(f"   ✅ {dc['name']} [{dc['code']}]")
        else:
            print("❌ KẾT QUẢ: TẤT CẢ ĐỀU HẾT HÀNG")
            for dc in asia_dcs:
                print(f"   ❌ {dc['name']} [{dc['code']}]")
        print("="*50)
        
        # Lưu HTML để debug
        with open('/tmp/ovh_asia_tab.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 Đã lưu HTML vào: /tmp/ovh_asia_tab.html")
        
        print("\n✅ Test thành công!")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False
    finally:
        if driver:
            print("\n🛑 Đóng browser...")
            driver.quit()

if __name__ == "__main__":
    success = test_ovh_asia_tab()
    sys.exit(0 if success else 1)
