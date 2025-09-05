import requests, json, sys

# --- load session.json ---
with open("session.json", "r") as f:
    session = json.load(f)

# ---- cookies ----
cookies = {}
if "cookies" in session:
    if isinstance(session["cookies"], str):
        for part in session["cookies"].split("; "):
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k] = v
    elif isinstance(session["cookies"], list):
        for c in session["cookies"]:
            if "name" in c and "value" in c:
                cookies[c["name"]] = c["value"]

# ---- headers ----
headers = {
    "content-type": "application/json",
    "accept": "text/event-stream",
    "origin": "https://duckduckgo.com",
    "referer": "https://duckduckgo.com/",
}
ua = session.get("headers", {}).get("user-agent")
vqd = session.get("headers", {}).get("x-vqd-hash-1")
if ua: headers["user-agent"] = ua
if vqd: headers["x-vqd-hash-1"] = vqd


# --- chat function ---
def chat(prompt: str):
    body = {
        "model": "gpt-4o-mini",
        "metadata": {"toolChoice": {
            "NewsSearch": False, "VideosSearch": False,
            "LocalSearch": False, "WeatherForecast": False
        }},
        "messages": [{"role": "user", "content": prompt}],
        "canUseTools": True,
        "canUseApproxLocation": False,
    }
    resp = requests.post(
        "https://duckduckgo.com/duckchat/v1/chat",
        headers=headers,
        cookies=cookies,
        data=json.dumps(body),
        stream=True,
    )
    full = []
    for line in resp.iter_lines():
        if not line or not line.startswith(b"data: "):
            continue
        payload = line[len(b"data: "):].decode()
        if payload == "[DONE]":
            break
        try:
            obj = json.loads(payload)
            msg = obj.get("message", "")
            if msg:
                full.append(msg)
                print(msg, end="", flush=True)  # live streaming
        except Exception:
            continue
    print("\n")
    return "".join(full)


# --- interactive loop ---
print("💬 Duck.ai interactive chat (type 'exit' to quit)")
while True:
    try:
        prompt = input("\nYou: ").strip()
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        print("Assistant: ", end="", flush=True)
        answer = chat(prompt)
        # optionally: keep conversation context
        # for now, it's stateless (only sends current user msg)
    except KeyboardInterrupt:
        print("\nBye!")
        break
