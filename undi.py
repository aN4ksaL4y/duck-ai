# import undetected_chromedriver as uc
from seleniumwire import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from icecream import ic
import time, re

# icecream config
ic.configureOutput(prefix='🐛 Debug | ')

options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
driver = uc.Chrome(options=options, version_main=139, headless=False)

ic("Launching Chrome...")
driver.get("https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat&duckai=1")

# after driver.get(...)
try:
    # look for ANY visible & clickable button in the top-most dialog/overlay
    btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='dialog'] button, div[role='alertdialog'] button, .ReactModalPortal button"))
    )
    ic("Found first-launch dialog button:", btn.text)
    btn.click()
    ic("Clicked the first dialog button")
except TimeoutException:
    ic("No visible launch dialog found")

# now wait until the overlay is actually gone
try:
    WebDriverWait(driver, 10).until_not(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], div[role='alertdialog'], .ReactModalPortal"))
    )
    ic("Dialog/overlay dismissed")
except TimeoutException:
    ic("No blocking overlay detected")

# only THEN get the chatbox
textbox = WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
)
ic("Chatbox interactable")

wait = WebDriverWait(driver, 30)

textbox = wait.until(
    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
)
ic("Chatbox ready")

query = "Make a 1000 words novel about quantum computing."
textbox.send_keys(query + Keys.ENTER)
ic("Sent query:", query)

# 🚀 infinite loop: keep dumping possible response nodes
ic("Entering infinite debug loop. Press Ctrl+C to stop manually.")

# seen_texts = set()

# def get_xpath(driver, element):
#     return driver.execute_script(
#         """
#         function getPath(el){
#             if (el.tagName === 'HTML') return '/HTML';
#             if (el === document.body) return '/HTML/BODY';
#             var ix=0;
#             var siblings=el.parentNode.childNodes;
#             for (var i=0; i<siblings.length; i++){
#                 var sib = siblings[i];
#                 if (sib === el)
#                     return getPath(el.parentNode) + '/' + el.tagName + '[' + (ix+1) + ']';
#                 if (sib.nodeType === 1 && sib.tagName === el.tagName)
#                     ix++;
#             }
#         }
#         return getPath(arguments[0]);
#         """, element)

# seen_texts = set()

def get_ai_responses():
    # Target the main response container
    elems = driver.find_elements(By.CSS_SELECTOR, "section div.PSL9z2mGqO2kEMN_ZOJl")
    results = []
    for e in elems:
        txt = e.text.strip()
        if txt:
            results.append(txt)
    return results

# optional: strip obvious UI noise so we stream just the model text
NOISE = [
    r"^\s*Duck\.ai.*$",
    r"^\s*FREE.*$",
    r"^\s*New Chat.*$",
    r"^\s*Share Feedback.*$",
    r"^\s*Open menu.*$",
    r"^\s*Search\s*$",
    r"^\s*Stop generating.*$",
    r"^\s*Generating response\.\.\.*$",
    r"^\s*Your chat with .* is private\..*$",
]
NOISE_RE = [re.compile(p) for p in NOISE]

def clean_text(s: str) -> str:
    lines = s.splitlines()
    kept = []
    for ln in lines:
        if any(rx.match(ln) for rx in NOISE_RE):
            continue
        kept.append(ln)
    # collapse extra blank lines
    out = "\n".join([l for l in kept if l.strip() != ""])
    return out

def get_last_clean_text():
    msgs = get_ai_responses()
    if not msgs:
        return ""
    return clean_text(msgs[-1])

# --- streaming once, via delta printing ---
ic("Waiting for first content from the response container…")
wait = WebDriverWait(driver, 60, poll_frequency=0.2)
# wait until container exists and has some non-noise text
wait.until(lambda d: len(get_last_clean_text()) > 0)

prev_len = 0
ic("Starting streaming… (Ctrl+C to stop)")

while True:
    # wait until the text length grows beyond prev_len
    wait.until(lambda d: len(get_last_clean_text()) > prev_len)
    current = get_last_clean_text()
    new_len = len(current)

    # compute and print delta only
    delta = current[prev_len:new_len]
    print(delta, end="", flush=True)

    prev_len = new_len
    # loop continues; when DDG appends more, the until() fires again