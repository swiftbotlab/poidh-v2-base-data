#!/home/agent/agent/browser-venv/bin/python -I
"""Render a PNG preview (summary + top rows) of a poidh v2 wallet CSV. Usage: render.py CSV SUMMARY.json OUT.png"""
import csv, json, sys
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
rows = list(csv.reader(open(sys.argv[1]))); S = json.load(open(sys.argv[2]))
W, H = 1600, 1000
im = Image.new("RGB", (W, H), (14, 17, 23)); d = ImageDraw.Draw(im)
def font(sz, bold=False):
    for p in (["/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"] if bold else []) + ["/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
G = (160, 200, 160); R = (235, 140, 120)
d.text((50, 36), f"poidh v2 on {S['chain'].capitalize()}: wallet data (exploit-excluded)", fill=(235, 235, 235), font=font(36, True))
d.text((50, 90), f"contract {S['contract']} · NFT {S['nft_contract'][:10]}...{S['nft_contract'][-4:]}", fill=(150, 150, 150), font=font(20))
ts = datetime.fromtimestamp(S["snapshot_time"], timezone.utc).strftime("%Y-%m-%d")
d.text((50, 125), f"{S['bounties']} bounties · {S['completed_legit']} legit completions · {S['cancelled']} cancelled · {S['open']} open · {S['rows']} wallets", fill=G, font=font(23))
d.text((50, 158), f"ETH paid out = ETH earned = {S['total_eth_paid_out'][:12]} (gross) · snapshot block {S['snapshot_block']} ({ts})", fill=G, font=font(23))
d.text((50, 191), f"NFTs: {S['nft_supply']} minted = {S['nfts_held_by_wallets_legit']} legit in wallets + {S['nfts_held_by_protocol_contract_legit']} legit in contract" + (f" + {S['nfts_held_by_wallets_exploit'] + S['nfts_held_by_protocol_contract_exploit']} exploit-minted" if S["completed_by_exploit"] else ""), fill=G, font=font(23))
if S["completed_by_exploit"]:
    d.text((50, 224), f"EXCLUDED: {S['completed_by_exploit']} exploit completions ({S['eth_taken_by_exploit_gross']} ETH) in {len(S['exploit_txs'])} txs; whitehat rescue (cancelled bounty) not counted", fill=R, font=font(23))
else:
    d.text((50, 224), "Dec 8 exploit did not touch this deployment: all completions issuer-accepted; whitehat rescue (cancelled) not counted", fill=R, font=font(21))
y = 280
hdr = ["address", "eth_paid_out", "eth_earned", "nfts_held"]
xs = [50, 760, 1040, 1320]
for x, h in zip(xs, hdr): d.text((x, y), h, fill=(255, 200, 90), font=font(24, True))
y += 40
for r in rows[1:22]:
    vals = [r[0], r[1][:12], r[2][:12], r[3]]
    for x, v in zip(xs, vals): d.text((x, y), v, fill=(220, 220, 220), font=font(22))
    y += 29
d.text((50, H - 45), f"top 21 of {len(rows)-1} rows by ETH earned · full CSV, method and exploit tx list in github.com/swiftbotlab/poidh-v2-base-data", fill=(140, 140, 140), font=font(20))
im.save(sys.argv[3]); print(sys.argv[3], im.size)
