import json, time
from seleniumwire import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.common.keys import Keys


options = uc.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-insecure-localhost")
options.add_argument("--ignore-ssl-errors=yes")

driver = uc.Chrome(version_main=139, options=options)

driver.get("https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat&duckai=1")

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

click_consent(driver)

# wait for chatbox to be usable
t = WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
)
t.send_keys("Ahoy there ducky!" + Keys.ENTER)
# capture session values
cookies = driver.get_cookies()
cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

x_vqd = None
timeout = time.time() + 30
while time.time() < timeout and not x_vqd:
    for req in driver.requests:
        if req.response and "/duckchat/v1/chat" in req.url:
            x_vqd = req.headers.get("x-vqd-hash-1")
            if x_vqd:
                print("[INFO] Captured x-vqd-hash-1:", x_vqd[:50], "...")
                break
    time.sleep(1)

if not x_vqd:
    print("[ERROR] Could not capture x-vqd-hash-1, exiting")

session = {
    "cookies": cookie_header,
    "headers": {
        "user-agent": driver.execute_script("return navigator.userAgent;"),
        "x-vqd-hash-1": x_vqd,
    },
}

with open("session.json", "w") as f:
    json.dump(session, f, indent=2)

print("[INFO] session.json updated")
driver.quit()
