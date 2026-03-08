import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

# Hackathon-scale synthetic dataset
NUM_ACCOUNTS = 250
NUM_CARDS = 220
NUM_DEVICES = 140
NUM_IPS = 160
NUM_MERCHANTS = 30
NUM_NORMAL_TXNS = 3500

NOW = datetime.now(timezone.utc)

RECORD_REF_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:[A-Za-z0-9_\-]+$")
DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}$")


def ts(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def rand_amount(low=5, high=250):
    return round(random.uniform(low, high), 2)


def format_value(v):
    if isinstance(v, str):
        if RECORD_REF_RE.match(v):
            return v
        if DATETIME_RE.match(v):
            return f'd"{v}"'
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "NONE"
    if isinstance(v, dict):
        inner = ", ".join(f"{k}: {format_value(val)}" for k, val in v.items())
        return "{ " + inner + " }"
    if isinstance(v, list):
        inner = ", ".join(format_value(x) for x in v)
        return "[ " + inner + " ]"
    return str(v)


def surreal_obj(d: dict) -> str:
    return "{ " + ", ".join(f"{k}: {format_value(v)}" for k, v in d.items()) + " }"


accounts = [f"account:acct_{i:03d}" for i in range(1, NUM_ACCOUNTS + 1)]
cards = [f"card:card_{i:03d}" for i in range(1, NUM_CARDS + 1)]
devices = [f"device:dev_{i:03d}" for i in range(1, NUM_DEVICES + 1)]
ips = [f"ip_address:ip_{i:03d}" for i in range(1, NUM_IPS + 1)]
merchants = [f"merchant:m_{i:03d}" for i in range(1, NUM_MERCHANTS + 1)]

out = []
out.append("USE NS hackathon DB agentic_auditor;")
out.append("")

# Fraud patterns
out += [
    'CREATE fraud_pattern:star CONTENT { name: "star_pattern", category: "smurfing", description: "One source rapidly sends to many destinations", severity_weight: 30 };',
    'CREATE fraud_pattern:cycle CONTENT { name: "circular_flow", category: "layering", description: "Funds move in a loop across accounts", severity_weight: 20 };',
    'CREATE fraud_pattern:flag_link CONTENT { name: "flagged_association", category: "association_risk", description: "Account linked to previously flagged account", severity_weight: 25 };',
    ""
]

# Merchants
merchant_categories = ["groceries", "electronics", "fashion", "fuel", "payments", "travel", "gaming", "crypto", "utilities"]
for i, m in enumerate(merchants, 1):
    out.append(
        f'CREATE {m} CONTENT {surreal_obj({"name": f"Merchant {i}", "category": random.choice(merchant_categories), "country": "GB", "metadata": {}})};'
    )

# Devices
for i, d in enumerate(devices, 1):
    out.append(
        f'CREATE {d} CONTENT {surreal_obj({"fingerprint": f"device-fp-{i:03d}", "first_seen_at": ts(random.randint(1000, 60000)), "metadata": {}})};'
    )

# IPs
cities = ["London", "Manchester", "Birmingham", "Leeds", "Bristol", "Liverpool", "Glasgow"]
for i, ip in enumerate(ips, 1):
    out.append(
        f'CREATE {ip} CONTENT {surreal_obj({"address": f"203.0.113.{i}", "asn": f"AS64{500+i}", "geo": {"country": "GB", "city": random.choice(cities)}, "metadata": {}})};'
    )

# Cards
brands = ["Visa", "Mastercard"]
for i, c in enumerate(cards, 1):
    out.append(
        f'CREATE {c} CONTENT {surreal_obj({"pan_last4": f"{random.randint(1000, 9999)}", "brand": random.choice(brands), "issued_at": ts(random.randint(5000, 90000)), "status": "active", "metadata": {}})};'
    )

# Accounts
flagged_accounts = {"account:acct_241", "account:acct_242", "account:acct_243"}
for i, a in enumerate(accounts, 1):
    confirmed = a in flagged_accounts
    out.append(
        f'CREATE {a} CONTENT {surreal_obj({"name": f"User {i}", "created_at": ts(random.randint(10000, 120000)), "risk_score": 75 if confirmed else random.randint(0, 18), "status": "active", "flagged_count": 3 if confirmed else 0, "confirmed_fraud": confirmed, "metadata": {"segment": random.choice(["consumer", "sole_trader", "small_business"])}})};'
    )

out.append("")

# Ownership / device / ip relations
for i, a in enumerate(accounts):
    if i < len(cards):
        out.append(
            f'RELATE {a}->owns_card->{cards[i % len(cards)]} CONTENT {{ since: d"{ts(random.randint(500, 12000))}" }};'
        )
    # 1-2 devices
    for _ in range(random.randint(1, 2)):
        dev = random.choice(devices)
        out.append(
            f'RELATE {a}->uses_device->{dev} CONTENT {{ first_seen_at: d"{ts(random.randint(300, 8000))}", last_seen_at: d"{ts(random.randint(1, 250))}", usage_count: {random.randint(1, 40)} }};'
        )
    # 1-2 ips
    for _ in range(random.randint(1, 2)):
        ip = random.choice(ips)
        out.append(
            f'RELATE {a}->uses_ip->{ip} CONTENT {{ first_seen_at: d"{ts(random.randint(300, 8000))}", last_seen_at: d"{ts(random.randint(1, 250))}", usage_count: {random.randint(1, 40)} }};'
        )

out.append("")

tx_counter = 1


def create_tx(src, dst, amount, minutes_ago, merchant, device, ip, channel="bank_transfer", status="completed"):
    global tx_counter
    tx = f"transaction:txn_{tx_counter:05d}"
    tx_id = f"txn_{tx_counter:05d}"
    tx_counter += 1

    tx_data = {
        "tx_id": tx_id,
        "amount": amount,
        "currency": "GBP",
        "ts": ts(minutes_ago),
        "channel": channel,
        "status": status,
        "source_account": src,
        "destination_account": dst,
        "card": random.choice(cards) if random.random() < 0.75 else None,
        "merchant": merchant,
        "device": device,
        "ip": ip,
        "location": {"country": "GB", "city": random.choice(cities)},
        "derived": {},
        "metadata": {}
    }

    stmt = f'CREATE {tx} CONTENT {surreal_obj(tx_data)};'
    return tx, stmt


# Normal history across first 230 accounts
normal_accounts = accounts[:230]
for _ in range(NUM_NORMAL_TXNS):
    src = random.choice(normal_accounts)
    dst = random.choice([a for a in normal_accounts if a != src])
    amt = rand_amount()
    mins = random.randint(60, 60 * 24 * 30)
    merchant = random.choice(merchants)
    device = random.choice(devices)
    ip = random.choice(ips)

    tx, stmt = create_tx(
        src, dst, amt, mins, merchant, device, ip,
        channel=random.choice(["bank_transfer", "card_transfer", "wallet"])
    )
    out.append(stmt)
    out.append(
        f'RELATE {src}->sent_to->{dst} CONTENT {{ tx_count: 1, total_amount: {amt}, first_tx_at: d"{ts(mins)}", last_tx_at: d"{ts(mins)}" }};'
    )

out.append("")

# 1 STAR PATTERN
# One source paying many recipients quickly
star_source = "account:acct_231"
star_targets = [f"account:acct_{i:03d}" for i in range(120, 161)]  # 41 targets
shared_device = "device:dev_002"
shared_ip = "ip_address:ip_002"

for idx, dst in enumerate(star_targets):
    amt = round(random.uniform(12, 48), 2)
    mins = 30 - min(idx, 29)
    tx, stmt = create_tx(star_source, dst, amt, mins, "merchant:m_005", shared_device, shared_ip, channel="card_transfer")
    out.append(stmt)
    out.append(
        f'RELATE {star_source}->sent_to->{dst} CONTENT {{ tx_count: 1, total_amount: {amt}, first_tx_at: d"{ts(mins)}", last_tx_at: d"{ts(mins)}" }};'
    )

out.append("")

# 2 CIRCULAR FLOW
# 5-node loop repeated 3 times
cycle_nodes = ["account:acct_232", "account:acct_233", "account:acct_234", "account:acct_235", "account:acct_236"]
for round_num in range(3):
    for i in range(len(cycle_nodes)):
        src = cycle_nodes[i]
        dst = cycle_nodes[(i + 1) % len(cycle_nodes)]
        amt = round(random.uniform(180, 260), 2)
        mins = 180 - (round_num * 30 + i * 6)
        tx, stmt = create_tx(src, dst, amt, mins, "merchant:m_006", "device:dev_003", "ip_address:ip_003", channel="bank_transfer")
        out.append(stmt)
        out.append(
            f'RELATE {src}->sent_to->{dst} CONTENT {{ tx_count: 1, total_amount: {amt}, first_tx_at: d"{ts(mins)}", last_tx_at: d"{ts(mins)}" }};'
        )

out.append("")

# 3 FLAGGED ASSOCIATION
# Accounts linked to prior flagged entities
assoc_sources = ["account:acct_237", "account:acct_238", "account:acct_239", "account:acct_240"]
shared_assoc_device = "device:dev_004"
shared_assoc_ip = "ip_address:ip_004"

for src in assoc_sources:
    for flagged in flagged_accounts:
        amt = rand_amount(35, 95)
        out.append(
            f'RELATE {src}->linked_to_flag->{flagged} CONTENT {{ reason: "shared device and repeated transfers", hops: 1, discovered_at: d"{ts(45)}" }};'
        )
        tx, stmt = create_tx(src, flagged, amt, random.randint(20, 80), "merchant:m_007", shared_assoc_device, shared_assoc_ip, channel="wallet")
        out.append(stmt)
        out.append(
            f'RELATE {src}->sent_to->{flagged} CONTENT {{ tx_count: 1, total_amount: {amt}, first_tx_at: d"{ts(35)}", last_tx_at: d"{ts(35)}" }};'
        )

out.append("")

# Bridge suspicious account across motifs
out.append(
    f'RELATE account:acct_231->linked_to_flag->account:acct_241 CONTENT {{ reason: "shared infrastructure", hops: 1, discovered_at: d"{ts(10)}" }};'
)

# Optional extra suspicious transactions to boost density
for dst in ["account:acct_241", "account:acct_242", "account:acct_243"]:
    amt = rand_amount(60, 140)
    tx, stmt = create_tx("account:acct_231", dst, amt, random.randint(5, 25), "merchant:m_008", shared_device, shared_ip, channel="wallet")
    out.append(stmt)
    out.append(
        f'RELATE account:acct_231->sent_to->{dst} CONTENT {{ tx_count: 1, total_amount: {amt}, first_tx_at: d"{ts(15)}", last_tx_at: d"{ts(15)}" }};'
    )

Path("seed.surql").write_text("\n".join(out), encoding="utf-8")
print("Wrote seed.surql")
print(f"Accounts: {NUM_ACCOUNTS}")
print(f"Normal transactions: {NUM_NORMAL_TXNS}")
print(f"Total transactions created: {tx_counter - 1}")