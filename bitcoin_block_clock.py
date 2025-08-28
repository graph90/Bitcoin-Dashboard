import tkinter as tk
from tkinter import font, Canvas
from datetime import datetime, timedelta
import random,threading,requests

COINGECKO_API = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
GLOBAL_API = "https://api.coingecko.com/api/v3/global"
BLOCKCHAIN_API = "https://blockstream.info/api/blocks/tip/height"
BLOCK_TIME = 10 * 60
INVEST_YEARS = 5
INVEST_AMOUNT = 100
MEMPOOL_API = "https://mempool.space/api/mempool"
FEES_API = "https://mempool.space/api/v1/fees/recommended"
PRICE_COOLDOWN = 60
DOMINANCE_COOLDOWN = 300
BLOCK_COOLDOWN = 30
MEMPOOL_COOLDOWN = 60
INVEST_UPDATE_INTERVAL = 300

last_block = 0
confetti_particles = []
last_price = None
btc_dominance = None
last_invest_update = datetime.min
next_block_estimate = datetime.now() + timedelta(seconds=BLOCK_TIME)

last_price_fetch = datetime.min
last_dominance_fetch = datetime.min
last_block_fetch = datetime.min
last_mempool_fetch = datetime.min

def get_btc_price_async():
    def worker():
        global last_price, last_price_fetch
        if (datetime.now() - last_price_fetch).seconds < PRICE_COOLDOWN:
            root.after(PRICE_COOLDOWN * 1000, get_btc_price_async)
            return
        try:
            resp = requests.get(COINGECKO_API, timeout=5)
            if resp.status_code == 429:
                print("Rate limited for BTC price. Retrying later...")
            else:
                data = resp.json()
                price = data['bitcoin']['usd']
                change = data['bitcoin']['usd_24h_change']
                last_price = price
                last_price_fetch = datetime.now()
                root.after(0, lambda: update_price_labels(price, change))
                root.after(0, lambda: update_investment(force=True))
        except Exception as e:
            print("Price fetch error:", e)
        finally:
            root.after(PRICE_COOLDOWN * 1000, get_btc_price_async)
    threading.Thread(target=worker, daemon=True).start()

def get_btc_dominance_async():
    def worker():
        global btc_dominance, last_dominance_fetch
        if (datetime.now() - last_dominance_fetch).seconds < DOMINANCE_COOLDOWN:
            root.after(DOMINANCE_COOLDOWN * 1000, get_btc_dominance_async)
            return
        try:
            resp = requests.get(GLOBAL_API, timeout=5)
            if resp.status_code == 429:
                print("Rate limited for BTC dominance. Retrying later...")
            else:
                data = resp.json()
                btc_dominance = data['data']['market_cap_percentage']['btc']
                last_dominance_fetch = datetime.now()
                root.after(0, lambda: update_dominance_label(btc_dominance))
        except Exception as e:
            print("Dominance fetch error:", e)
            root.after(0, lambda: update_dominance_label(None))
        finally:
            root.after(DOMINANCE_COOLDOWN * 1000, get_btc_dominance_async)
    threading.Thread(target=worker, daemon=True).start()

def update_price_labels(price, change):
    price_label.config(text=f"${price:,.2f}")
    change_label.config(text=f"{change:+.2f}%")
    change_label.config(fg="green" if change >= 0 else "red")

def update_dominance_label(dominance):
    if dominance is not None:
        dominance_label.config(text=f"BTC Dominance: {dominance:.2f}%")
    else:
        dominance_label.config(text="BTC Dominance: N/A")

def get_block_height_async():
    def worker():
        global last_block, next_block_estimate, last_block_fetch
        if (datetime.now() - last_block_fetch).seconds < BLOCK_COOLDOWN:
            root.after(BLOCK_COOLDOWN * 1000, get_block_height_async)
            return
        try:
            resp = requests.get(BLOCKCHAIN_API, timeout=5)
            if resp.status_code == 429:
                print("Rate limited for block height. Retrying later...")
            else:
                block_height = int(resp.text)
                last_block_fetch = datetime.now()
                root.after(0, lambda: update_block_labels(block_height))
        except Exception as e:
            print("Block height fetch error:", e)
        finally:
            root.after(BLOCK_COOLDOWN * 1000, get_block_height_async)
    threading.Thread(target=worker, daemon=True).start()

def update_block_labels(block_height):
    global last_block, next_block_estimate
    block_label.config(text=f"Block: {block_height}")
    if block_height > last_block:
        create_confetti(50)
        last_block = block_height
        next_block_estimate = datetime.now() + timedelta(seconds=BLOCK_TIME)

def get_mempool_stats_async():
    def worker():
        global last_mempool_fetch
        if (datetime.now() - last_mempool_fetch).seconds < MEMPOOL_COOLDOWN:
            root.after(MEMPOOL_COOLDOWN * 1000, get_mempool_stats_async)
            return
        try:
            mempool = requests.get(MEMPOOL_API, timeout=5).json()
            fees = requests.get(FEES_API, timeout=5).json()
            mempool_count = mempool.get("count", 0)
            fast = fees.get("fastestFee", 0)
            half = fees.get("halfHourFee", 0)
            hour = fees.get("hourFee", 0)
            last_mempool_fetch = datetime.now()
            root.after(0, lambda: update_mempool_labels(mempool_count, fast, half, hour))
        except Exception as e:
            print("Mempool fetch error:", e)
            root.after(0, lambda: update_mempool_labels(None, None, None, None))
        finally:
            root.after(MEMPOOL_COOLDOWN * 1000, get_mempool_stats_async)
    threading.Thread(target=worker, daemon=True).start()

def update_mempool_labels(count, fast, half, hour):
    if count is not None:
        mempool_label.config(text=f"Mempool: {count:,} tx")
        fees_label.config(text=f"Fees → Fast: {fast} | 30m: {half} | 1h: {hour} sat/vB")
    else:
        mempool_label.config(text="Mempool: N/A")
        fees_label.config(text="Fees: N/A")

def calc_investment_value(current_price, past_price):
    return INVEST_AMOUNT * (current_price / past_price)

def update_investment(force=False):
    global last_invest_update
    if last_price and (force or last_invest_update == datetime.min or
        (datetime.now() - last_invest_update).seconds > INVEST_UPDATE_INTERVAL):
        past_price = last_price / 15
        invest_value = calc_investment_value(last_price, past_price)
        invest_label.config(text=f"$100 invested 5 yrs ago → ${invest_value:,.2f}")
        last_invest_update = datetime.now()
    root.after(INVEST_UPDATE_INTERVAL * 1000, update_investment)

def create_confetti(count=30):
    btc_colors = ["#f7931a", "#ffffff", "#ffd700"]
    for _ in range(count):
        x = random.randint(0, 500)
        y = random.randint(-50, 0)
        size = random.randint(5, 15)
        color = random.choice(btc_colors)
        speed = random.uniform(1, 4)
        oid = canvas.create_oval(
            x, y, x + size, y + size,
            fill=color, outline="", tags="confetti"
        )
        confetti_particles.append({
            "id": oid,
            "x": x,
            "y": y,
            "size": size,
            "color": color,
            "speed": speed
        })

def animate_confetti():
    for p in confetti_particles:
        p["y"] += p["speed"]
        if p["y"] > 200:
            p["y"] = random.randint(-50, 0)
            p["x"] = random.randint(0, 500)
        canvas.coords(
            p["id"],
            p["x"], p["y"],
            p["x"] + p["size"], p["y"] + p["size"]
        )
    root.after(30, animate_confetti)

def update_countdown():
    remaining = next_block_estimate - datetime.now()
    total_seconds = max(int(remaining.total_seconds()), 0)
    minutes, seconds = divmod(total_seconds, 60)
    countdown_timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
    root.after(1000, update_countdown)

root = tk.Tk()
root.title("Bitcoin Dashboard")
root.geometry("500x650")
root.config(bg="#121212")

title_font = font.Font(family="Comic Sans MS", size=24, weight="bold")
big_font = font.Font(family="Comic Sans MS", size=18, weight="bold")
medium_font = font.Font(family="Comic Sans MS", size=14)

canvas = Canvas(root, width=500, height=200, bg="#121212", highlightthickness=0)
canvas.pack()
create_confetti(30)
animate_confetti()

tk.Label(root, text="Bitcoin Block Clock", font=title_font, bg="#121212", fg="#f7931a").pack(pady=5)
block_label = tk.Label(root, font=big_font, bg="#121212", fg="white")
block_label.pack()
countdown_timer_label = tk.Label(root, font=big_font, bg="#121212", fg="#f7931a")
countdown_timer_label.pack(pady=5)

tk.Label(root, text="BTC Price", font=title_font, bg="#121212", fg="#f7931a").pack(pady=5)
price_label = tk.Label(root, font=big_font, bg="#121212", fg="white")
price_label.pack()
change_label = tk.Label(root, font=big_font, bg="#121212")
change_label.pack(pady=5)
dominance_label = tk.Label(root, font=medium_font, bg="#121212", fg="white")
dominance_label.pack(pady=2)

invest_label = tk.Label(root, font=big_font, bg="#121212", fg="yellow")
invest_label.pack(pady=10)

mempool_label = tk.Label(root, font=medium_font, bg="#121212", fg="white")
mempool_label.pack(pady=2)
fees_label = tk.Label(root, font=medium_font, bg="#121212", fg="white")
fees_label.pack(pady=2)

get_btc_price_async()
get_btc_dominance_async()
get_block_height_async()
get_mempool_stats_async()
update_investment()
update_countdown()

root.mainloop()
