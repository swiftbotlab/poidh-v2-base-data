#!/usr/bin/env python3
"""Build the per-wallet CSV for one poidh v2 deployment from the pinned-block state dump (fetch_state.py) and the
acceptance classification (classify.py). Exact wei arithmetic; ETH printed with Decimal.
Usage: build_csv.py STATE.json ACCEPT_CLASS.json JOIN_LOGS.json OUT.csv SUMMARY.json [EXCLUDED_TXS.json]"""
import csv, json, sys, collections, os
from decimal import Decimal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from events import dec

statef, classf, joinf, outcsv, outsum = sys.argv[1:6]
st = json.load(open(statef)); B = st["bounties"]; CL = st["claims"]; OWN = st["owners"]
cls = json.load(open(classf))
joins = json.load(open(joinf))["result"]
Z = "0x0000000000000000000000000000000000000000"
CONTRACT = next(b for b in [st["contract"]]); 
from eth_utils import to_checksum_address as cs
CONTRACT = cs(CONTRACT)

LEGIT_HOW = {"acceptClaim by issuer", "acceptClaim by issuer (4337 smart wallet)", "resolveVote, vote opened by issuer",
             "resolveVote, vote opened by issuer (4337)", "resolveVote (4337 caller), vote opened by issuer"}
how = {}  # bounty id -> how it was accepted
exploit_txs = collections.defaultdict(list)
for key, o in cls.items():
    how[o["bounty"]] = o["how"]
    if o["how"] not in LEGIT_HOW:
        exploit_txs[key.split(":")[0]].append(o["bounty"])

paid = collections.Counter(); earned = collections.Counter(); n_funded = collections.Counter(); n_won = collections.Counter()
wallets = set(); exploit_bounties = []; legit = []
for b in B:
    wallets.add(b["issuer"])
    for p, a in b["participants"]:
        if p != Z: wallets.add(p)
    if b["claimer"] in (Z, b["issuer"]):  # open (claimer 0) or cancelled (cancel sets claimer = issuer)
        continue
    c = CL[b["claimId"]]
    assert c["bountyId"] == b["id"] and c["accepted"] and c["issuer"] == b["claimer"], b["id"]
    if b["id"] not in how:
        raise SystemExit(f"completed bounty {b['id']} has no ClaimAccepted event")
    if how[b["id"]] not in LEGIT_HOW:
        exploit_bounties.append(b["id"]); continue
    legit.append(b["id"])
    amt = int(b["amount"])
    earned[b["claimer"]] += amt; n_won[b["claimer"]] += 1; wallets.add(b["claimer"])
    ps = [(p, int(a)) for p, a in b["participants"] if p != Z and int(a) > 0]
    if not ps:  # solo bounty: the issuer funded all of it
        ps = [(b["issuer"], amt)]
    assert sum(a for _, a in ps) == amt, f"contributions != amount on bounty {b['id']}"
    for p, a in ps:
        paid[p] += a; n_funded[p] += 1
assert len(legit) + len(exploit_bounties) == len(cls), "event/state mismatch"
for l in joins:  # contributors who joined (and maybe withdrew) an open bounty
    wallets.add(cs(dec(l)[1][1]))
for c in CL:
    wallets.add(c["issuer"])

exploit_claim_ids = {B[b]["claimId"] for b in exploit_bounties}
exploit_claimers = {B[b]["claimer"] for b in exploit_bounties}
# exploit claims that were created but never accepted (same claimer contracts, same txs): their NFTs are not legit either
for c in CL:
    if c["issuer"] in exploit_claimers:
        exploit_claim_ids.add(c["id"])
held = collections.Counter(); held_exploit = collections.Counter()
for t, o in OWN.items():
    (held_exploit if int(t) in exploit_claim_ids else held)[o] += 1
in_contract = held.pop(CONTRACT, 0); in_contract_exploit = held_exploit.pop(CONTRACT, 0)
wallets |= set(held) | set(held_exploit)
wallets.discard(CONTRACT); wallets.discard(Z)

notes = {}
for w in exploit_claimers: notes[w] = "exploit attacker contract (claims excluded)"
for w in json.load(open(sys.argv[6])).get("labels", {}).items() if len(sys.argv) > 6 else []:
    notes[cs(w[0])] = w[1]

def eth(wei):
    q = (Decimal(wei) / Decimal(10**18)).normalize()
    return format(q, "f") if q != 0 else "0"

rows = sorted(wallets, key=lambda w: (-earned[w], -paid[w], -held[w], w))
with open(outcsv, "w", newline="") as f:
    wr = csv.writer(f)
    wr.writerow(["address", "eth_paid_out", "eth_earned", "nfts_held", "bounties_funded_completed", "bounties_won", "exploit_nfts_held", "note"])
    for w in rows:
        wr.writerow([w, eth(paid[w]), eth(earned[w]), held[w], n_funded[w], n_won[w], held_exploit[w], notes.get(w, "")])
stolen = sum(int(B[b]["amount"]) for b in exploit_bounties)
S = {"chain": st["chain"], "contract": st["contract"], "nft_contract": st["nft"], "snapshot_block": st["block"], "snapshot_time": st["block_time"],
     "bounties": len(B), "completed_onchain": len(legit) + len(exploit_bounties), "completed_legit": len(legit),
     "completed_by_exploit": len(exploit_bounties), "exploit_bounty_ids": sorted(exploit_bounties),
     "exploit_txs": {h: sorted(v) for h, v in exploit_txs.items()}, "eth_taken_by_exploit_gross": eth(stolen),
     "cancelled": sum(1 for b in B if b["claimer"] == b["issuer"]), "open": sum(1 for b in B if b["claimer"] == Z),
     "rows": len(rows), "total_eth_paid_out": eth(sum(paid.values())), "total_eth_earned": eth(sum(earned.values())),
     "nft_supply": st["nft_supply"], "nfts_held_by_wallets_legit": sum(held.values()), "nfts_held_by_wallets_exploit": sum(held_exploit.values()),
     "nfts_held_by_protocol_contract_legit": in_contract, "nfts_held_by_protocol_contract_exploit": in_contract_exploit,
     "how_accepted": dict(collections.Counter(how.values()))}
assert sum(paid.values()) == sum(earned.values())
assert S["nfts_held_by_wallets_legit"] + S["nfts_held_by_wallets_exploit"] + in_contract + in_contract_exploit == st["nft_supply"] == len(OWN)
json.dump(S, open(outsum, "w"), indent=1)
print(json.dumps(S, indent=1))
