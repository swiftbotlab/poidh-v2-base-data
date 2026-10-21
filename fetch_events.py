#!/usr/bin/env python3
"""Download every PoidhV2 event of one type from Blockscout's etherscan-compatible logs API (keyless; <1000 per type here).
Usage: fetch_events.py base|arbitrum OUTDIR. Writes OUTDIR/{acc,vote,voteclaim,reset,cancel,withdraw,join}.json.
Note: Blockscout sits behind Cloudflare; from some networks this needs a browser session (same URLs via fetch())."""
import json, sys, urllib.request
from eth_utils import keccak
HOST = {"base": ("https://base.blockscout.com", "0xb502c5856f7244dccdd0264a541cc25675353d39"),
        "arbitrum": ("https://arbitrum.blockscout.com", "0x0aa50ce0d724cc28f8f7af4630c32377b4d5c27d")}
EV = {"acc": "ClaimAccepted(uint256,uint256,address,address,uint256)", "vote": "ClaimSubmittedForVote(uint256,uint256)",
      "voteclaim": "VoteClaim(address,uint256,uint256)", "reset": "ResetVotingPeriod(uint256)", "cancel": "BountyCancelled(uint256,address)",
      "withdraw": "WithdrawFromOpenBounty(uint256,address,uint256)", "join": "BountyJoined(uint256,address,uint256)"}
host, addr = HOST[sys.argv[1]]
for k, sig in EV.items():
    url = f"{host}/api?module=logs&action=getLogs&address={addr}&topic0=0x{keccak(text=sig).hex()}&fromBlock=0&toBlock=latest"
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=60))
    assert len(d["result"]) < 1000, "paginate by block range"
    json.dump(d, open(f"{sys.argv[2]}/{k}.json", "w")); print(k, len(d["result"]))
