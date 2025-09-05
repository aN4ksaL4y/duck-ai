from seleniumwire import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import json
from bs4 import BeautifulSoup



# launch stealth chrome
options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = uc.Chrome(options=options, version_main=139)

driver.get("https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat&duckai=1")

def wait_and_click_consent_infinite(driver, poll=1):
    """
    Retry forever until:
      - a consent button (ok/accept/got it/continue/yes) is found -> click & stop
      - or chatbox textarea appears -> stop (no consent shown)
    """
    while True:
        # list all buttons and log their text
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit']")
        if buttons:
            print("[DEBUG] Found buttons:", [ (b.text or "").strip() for b in buttons ])
        for b in buttons:
            label = (b.text or "").strip().lower()
            if label in {"ok", "accept", "got it", "continue", "yes"}:
                b.click()
                print(f"[INFO] Clicked consent button: {label}")
                return True

        # if chatbox already present, stop retrying
        try:
            driver.find_element(By.TAG_NAME, "textarea")
            print("[INFO] Chatbox ready, no consent dialog")
            return False
        except NoSuchElementException:
            pass

        time.sleep(poll)


def brute_force_click(driver, poll=1):
    while True:
        elems = driver.find_elements(By.CSS_SELECTOR, "button, [role='button'], a, div, span")
        for e in elems:
            try:
                e.click()
                print("[INFO] Clicked element:", (e.text or "").strip(), e.get_attribute("class"))
                return True
            except Exception:
                continue
        # check chatbox ready
        try:
            driver.find_element(By.TAG_NAME, "textarea")
            print("[INFO] Chatbox ready")
            return False
        except:
            pass
        print("[DEBUG] No consent element yet, retrying...")
        time.sleep(poll)


def dump_dom(driver, limit=5000):
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    def walk(node, depth=0):
        if depth > 4:   # don’t go too deep unless you want EVERYTHING
            return
        if node.name:
            attrs = " ".join([f'{k}="{v}"' for k,v in node.attrs.items()])
            text = (node.get_text(strip=True)[:60] if node.get_text(strip=True) else "")
            print("  " * depth + f"<{node.name} {attrs}> {text}")
            for child in node.children:
                walk(child, depth+1)

    body = soup.find("body")
    walk(body)

def walk_shadow_dom(driver, root=None, depth=0, max_depth=5):
    """
    Recursively walk DOM + shadow roots to find clickable elements.
    """
    if depth > max_depth:
        return

    if root is None:
        # start from document root
        elements = driver.find_elements(By.CSS_SELECTOR, "*")
    else:
        # query inside a shadow root
        elements = driver.execute_script("return arguments[0].querySelectorAll('*')", root)

    for el in elements:
        try:
            shadow = driver.execute_script("return arguments[0].shadowRoot", el)
        except Exception:
            shadow = None

        if shadow:
            print("  " * depth + f"[SHADOW HOST] <{el.tag_name}> class='{el.get_attribute('class')}'")
            walk_shadow_dom(driver, root=shadow, depth=depth+1, max_depth=max_depth)

        # collect candidate clickables
        tag = el.tag_name.lower()
        role = el.get_attribute("role")
        if tag in {"button", "a"} or role == "button" or tag == "div":
            label = (el.text or "").strip()
            aria = el.get_attribute("aria-label")
            cls = el.get_attribute("class")
            if label or aria:
                print("  " * depth + f"CANDIDATE <{tag}> text='{label}' aria='{aria}' class='{cls}'")


def click_consent(driver, timeout=30):
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By

    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Agree and Continue')]"))
        )
        driver.execute_script("arguments[0].click()", btn)
        print("[INFO] Clicked consent: 'Agree and Continue'")
        return True
    except Exception as e:
        print("[WARN] Consent button not found:", e)
        return False

time.sleep(10)
click_consent(driver)


textbox = WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
)
textbox.send_keys("Hello network capture!" + Keys.ENTER)

print("[INFO] Started logging network requests. Press Ctrl+C to stop.")

with open("requests_log.txt", "w", encoding="utf-8") as f:
    try:
        while True:
            for req in driver.requests:
                if not req.response:
                    continue
                if req.method == "POST":  # filter only Duck.ai traffic
                    entry = {
                        "url": req.url,
                        "method": req.method,
                        "status": req.response.status_code,
                        "headers": dict(req.headers),
                        "response_headers": dict(req.response.headers),
                        "body": req.body.decode("utf-8", errors="ignore") if req.body else None,
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    f.flush()
                    print("[LOGGED]", req.method, req.url, "->", req.response.status_code)
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO] Logging stopped by user (Ctrl+C).")
