import pandas as pd
import time
import os
import re
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Hardened Global Configuration File Path Alignment Map
DB_FILE = "D:\\Afsal\\Whatsapp_bot\\inventory.csv"
FORCE_CATCH_UP = True  

def clean_data_file():
    if os.path.exists(DB_FILE):
        for attempt in range(3):
            try:
                df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
                df.columns = df.columns.str.strip()
                if 'Last_4' in df.columns:
                    df['Last_4'] = df['Last_4'].astype(str).str.split('.').str[0].str.strip()
                df.to_csv(DB_FILE, index=False)
                print("📊 Inventory local storage file synchronized successfully.")
                return
            except PermissionError:
                time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Error preparing CSV file: {e}")
                return

def dispatch_reply_message(driver, text_to_send):
    message_sent = False
    try:
        active_el = driver.switch_to.active_element
        if active_el and active_el.get_attribute("contenteditable") == "true":
            active_el.send_keys(text_to_send)
            time.sleep(0.5)
            active_el.send_keys(Keys.ENTER)
            message_sent = True
    except:
        pass
    
    if not message_sent:
        css_selectors = [
            'footer *[contenteditable="true"]', 
            'div[contenteditable="true"][role="textbox"]',
            'div[data-lexical-editor="true"]'
        ]
        for css_sel in css_selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, css_sel)
                if el:
                    actions = ActionChains(driver)
                    actions.move_to_element(el).click().send_keys(text_to_send).perform()
                    time.sleep(0.5)
                    el.send_keys(Keys.ENTER)
                    message_sent = True
                    break
            except:
                continue
                
    return message_sent

def scan_live_sidebar(driver):
    global FORCE_CATCH_UP
    
    # Fault-tolerant master read loop to accommodate parallel edits from dashboard
    df = None
    for attempt in range(3):
        try:
            df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            break
        except PermissionError:
            time.sleep(0.5)
            
    if df is None:
        return

    df['Last_4'] = df['Last_4'].astype(str).str.split('.').str[0].str.strip()
    pending_codes = df[df['Status'] == 'Pending']['Last_4'].tolist()
    
    if not pending_codes:
        print(f"💤 Radar Idle [{datetime.now().strftime('%H:%M:%S')}]: Zero pending orders found in database.")
        return

    if FORCE_CATCH_UP:
        print(f"⚡ CATCH-UP ACTIVE [{datetime.now().strftime('%H:%M:%S')}]: Processing history sweeps...")
    else:
        print(f"📡 Radar Scan [{datetime.now().strftime('%H:%M:%S')}]: Filtering top 5 active chats...")

    database_updated = False

    # Scans top 5 chats sequentially regardless of read/unread flags
    for idx in range(5):
        try:
            # Resilient target matching standard row list items or updated elements
            chats = driver.find_elements(By.XPATH, '//div[@role="listitem"] | //div[contains(@class, "_ak8l")] | //div[@role="row"]')
            if not chats or idx >= len(chats):
                break
                
            chat = chats[idx]
            
            print(f"🔓 Opening chat index tier {idx+1}...")
            clicked = False
            inner_elements = chat.find_elements(By.XPATH, './/span[@title] | .//div[contains(@class, "_ak8j")] | .//span')
            if inner_elements:
                try:
                    actions = ActionChains(driver)
                    actions.move_to_element(inner_elements[0]).click().perform()
                    clicked = True
                except:
                    pass
            
            if not clicked:
                driver.execute_script("arguments[0].click();", chat)
                
            time.sleep(2.0)  # Wait for conversation view container elements to shift open

            # Scrapes text inside message arrays safely
            message_bubbles = driver.find_elements(By.XPATH, '//*[contains(@data-id, "false_")]')
            if not message_bubbles:
                message_bubbles = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in")]')
            if not message_bubbles:
                message_bubbles = driver.find_elements(By.XPATH, '//div[@data-pre-plain-text]')

            if not message_bubbles:
                continue

            combined_text_pool = ""
            for bubble in message_bubbles:
                raw_bubble_text = bubble.text
                if raw_bubble_text:
                    clean_text = re.sub(r'\b\d{1,2}:\d{2}\b', '', raw_bubble_text)
                    clean_text = re.sub(r'\b(AM|PM)\b', '', clean_text, flags=re.IGNORECASE)
                    combined_text_pool += "\n" + clean_text

            found_codes = re.findall(r'\b\d{4}\b', combined_text_pool)
            if not found_codes:
                continue

            for code in list(dict.fromkeys(found_codes)):
                match = df[(df['Last_4'] == str(code).strip()) & (df['Status'] == 'Pending')]
                
                if not match.empty:
                    row_idx = match.index[0]
                    full_do = df.loc[row_idx, 'DO_Number']
                    
                    print(f"🎯 MATCH CONFIRMED: Code '{code}' aligns with order {full_do}")
                    confirmation_msg = f"System Received! {full_do} has been marked as Dispatched. 👍"
                    
                    if dispatch_reply_message(driver, confirmation_msg):
                        print(f"   🚀 Confirmation message dispatched.")
                        df.loc[row_idx, 'Status'] = 'Dispatched'
                        database_updated = True
                        time.sleep(1.0)  
                    else:
                        print(f"   ❌ Network failure updating tracking code: {code}")
        except Exception as e:
            continue

    if database_updated:
        # Save modifications with explicit file lockout protection handling loops
        for attempt in range(3):
            try:
                df.to_csv(DB_FILE, index=False)
                print("✅ CSV Database fully updated and rewritten.")
                break
            except PermissionError:
                time.sleep(0.5)

    if FORCE_CATCH_UP:
        FORCE_CATCH_UP = False
        print("⚙️ Batch sweep completed. Re-centering radar on live standby.\n")


def background_whatsapp_radar_loop(stop_event):
    """
    Unified entry-point designed to be safely driven by Streamlit's interface threading model.
    """
    print("==================================================")
    print("  💎 CONTINUOUS SWEEP PIPELINE (v4.3-TopFive)      ")
    print("==================================================")
    
    clean_data_file()
    
    print("\n🚀 Launching Automated Chrome Window...")
    options = webdriver.ChromeOptions()
    script_dir = "D:\\Afsal\\Whatsapp_bot"
    profile_path = os.path.join(script_dir, "selenium_whatsapp_data")
    
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--remote-debugging-port=9222") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")
        
        print("⏳ WAITING: Please scan the QR code on your screen if logged out...")
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
        )
        print("✅ WhatsApp Web Fully Connected and Loaded!")
        print("\n🟢 RADAR RUNNING...")
        
        # Runs infinitely until the stop_event is set from the dashboard UI sidebar
        while not stop_event.is_set():
            scan_live_sidebar(driver)
            time.sleep(5)
            
    except Exception as e:
        print(f"🚨 Critical exception in bot runtime: {e}")
    finally:
        if driver:
            print("🛑 Closing automated browser context cleanly...")
            try:
                driver.quit()
            except:
                pass
        print("⚙️ Background worker process context ended.")


# Allows file to still be run as a standalone terminal script if you want to test it separately
if __name__ == "__main__":
    stop_event = threading.Event()
    try:
        background_whatsapp_radar_loop(stop_event)
    except KeyboardInterrupt:
        print("\nStopping loop via hardware terminal interrupt...")
        stop_event.set()