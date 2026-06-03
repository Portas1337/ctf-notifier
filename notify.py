#!/usr/bin/env python3
import json
import os
import time
import sys
import urllib.request
import urllib.error

CTFTIME_API = "https://ctftime.org/api/v1/events/"
SEEN_FILE   = "seen_events.json"
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

DAYS_AHEAD  = int(os.environ.get("DAYS_AHEAD", "14"))
MIN_WEIGHT  = float(os.environ.get("MIN_WEIGHT", "0"))

HEADERS = {"User-Agent": "CTFtime-Notifier/1.0"}


def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def fetch_events():
    now    = int(time.time())
    finish = now + DAYS_AHEAD * 86400
    url = f"{CTFTIME_API}?limit=100&start={now}&finish={finish}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def color_for(weight):
    if weight >= 50:
        return 0xFFD700   # ouro
    if weight >= 25:
        return 0x3498DB   # azul
    return 0x2ECC71       # verde


def build_embed(event):
    start  = event.get("start", "")[:16].replace("T", " ")
    finish = event.get("finish", "")[:16].replace("T", " ")
    weight = event.get("weight", 0)
    ctftime_url = f"https://ctftime.org/event/{event['id']}"

    fields = [
        {"name": "📅 Início",  "value": f"{start} UTC",  "inline": True},
        {"name": "🏁 Fim",     "value": f"{finish} UTC", "inline": True},
        {"name": "⚖️ Peso",    "value": str(weight),     "inline": True},
        {"name": "🌐 Formato", "value": event.get("format", "?"), "inline": True},
        {"name": "🔗 Site",    "value": event.get("url") or "N/A", "inline": True},
    ]

    desc = (event.get("description") or "")[:300]

    embed = {
        "title": f"🚩 {event['title']}",
        "url": ctftime_url,
        "color": color_for(weight),
        "fields": fields,
        "footer": {"text": "CTFtime Notifier"},
    }
    if desc:
        embed["description"] = desc
    if event.get("logo"):
        embed["thumbnail"] = {"url": event["logo"]}
    return embed


def send_to_discord(embeds):
    # Discord aceita no máximo 10 embeds por mensagem
    for i in range(0, len(embeds), 10):
        payload = {"embeds": embeds[i:i + 10]}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            WEBHOOK_URL, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as e:
            print(f"[ERRO] Discord retornou {e.code}: {e.read().decode()}")
            sys.exit(1)
        time.sleep(1)  # evita rate limit


def main():
    seen = load_seen()
    events = fetch_events()

    new_embeds = []
    for event in events:
        eid = str(event["id"])
        if eid in seen:
            continue
        if event.get("weight", 0) < MIN_WEIGHT:
            seen.add(eid)   # marca pra não reavaliar sempre
            continue
        new_embeds.append(build_embed(event))
        seen.add(eid)

    if new_embeds:
        send_to_discord(new_embeds)
        print(f"[INFO] {len(new_embeds)} novos CTFs notificados.")
    else:
        print("[INFO] Nenhum CTF novo.")

    save_seen(seen)


if __name__ == "__main__":
    main()
