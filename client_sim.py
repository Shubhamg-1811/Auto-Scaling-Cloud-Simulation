import requests, random, time

LB_URL = "http://127.0.0.1:8000"
PAGES = ["page1","page2","page3"]

print("[Client] Starting client simulator...")
while True:
    page = random.choice(PAGES)
    try:
        r = requests.get(f"{LB_URL}/{page}", timeout=5)
        print(f"[Client] Request to '{page}' -> Status: {r.status_code} | Response: {r.text.strip()}")
    except requests.exceptions.RequestException as e:
        print(f"[Client] Request to '{page}' -> ERROR: {e}")
    
    seconds_in_minute = time.time() % 60
    if 20 <= seconds_in_minute <= 40:
        sleep_time = random.uniform(0.01, 0.05)
    else:
        sleep_time = random.uniform(0.2, 1.0)
    time.sleep(sleep_time)
