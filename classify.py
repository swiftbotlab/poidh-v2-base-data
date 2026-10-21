"""Classify every ClaimAccepted on a poidh v2 deployment by HOW it was accepted (who called, via what)."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import rpc
from events import dec
from eth_abi import decode
from eth_utils import keccak, to_checksum_address as cs
from collections import Counter, defaultdict
chain, statef, bsdir, contract = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].lower()
rpc.CHAIN = chain
st = json.load(open(statef)); B = st["bounties"]
T = json.load(open(f"{bsdir}/txinfo.json"))
acc = json.load(open(f"{bsdir}/acc.json"))["result"]; votes = json.load(open(f"{bsdir}/vote.json"))["result"]
sel_ro = "0x" + keccak(text="resolveVote(uint256)")[:4].hex()
EP = ("0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789", "0x0000000071727de22e5e9d8baf0edac6f37da032")
sv = defaultdict(list)
for l in votes:
    n, v = dec(l); sv[(v[0], v[1])].append((int(l["blockNumber"], 16), l["transactionHash"]))
def ops_senders(h):
    t = rpc.call("eth_getTransactionByHash", [h]); data = bytes.fromhex(t["input"][10:])
    if t["input"][:10] == "0x1fad948c":
        ops, _ = decode(["(address,uint256,bytes,bytes,uint256,uint256,uint256,uint256,uint256,bytes,bytes)[]", "address"], data)
    else:
        ops, _ = decode(["(address,uint256,bytes,bytes,bytes32,uint256,bytes32,bytes,bytes)[]", "address"], data)
    return [cs(o[0]) for o in ops]
c = Counter(); out = {}
for l in acc:
    n, v = dec(l); bid, cid = v[0], v[1]; h = l["transactionHash"]; t = T[h]; iss = B[bid]["issuer"]; blk = int(l["blockNumber"], 16)
    to = (t["to"] or "").lower()
    if to == contract and t["sel"] == sel_ro:
        subs = [x for x in sv[(bid, cid)] if x[0] <= blk]
        sh = subs[-1][1] if subs else None
        sto = (T[sh]["to"] or "").lower() if sh else ""
        if not sh: k = "resolveVote: no submit found"
        elif cs(T[sh]["from"]) == iss: k = "resolveVote, vote opened by issuer"
        elif sto in EP: k = "resolveVote, vote opened by issuer (4337)" if iss in ops_senders(sh) else "resolveVote, vote opened by NON-issuer (4337)"
        else: k = "resolveVote, vote opened by NON-issuer"
        out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k, "vote_tx": sh}
    elif to in EP:
        full = rpc.call("eth_getTransactionByHash", [h])["input"]
        if sel_ro[2:] in full:  # smart-wallet batch that calls resolveVote: judge by who opened the vote
            subs = [x for x in sv[(bid, cid)] if x[0] <= blk]
            sh = subs[-1][1] if subs else None
            sto = (T[sh]["to"] or "").lower() if sh else ""
            if not sh: k = "resolveVote (4337): no submit found"
            elif cs(T[sh]["from"]) == iss or (sto in EP and iss in ops_senders(sh)): k = "resolveVote (4337 caller), vote opened by issuer"
            else: k = "resolveVote (4337 caller), vote opened by NON-issuer"
            out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k, "vote_tx": sh}
        else:
            k = "acceptClaim by issuer (4337 smart wallet)" if iss in ops_senders(h) else "acceptClaim via 4337, NOT issuer"
            out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k}
    elif not t["to"]:
        k = "contract-creation tx (exploit)"
        out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k, "from": t["from"]}
    elif to == contract:
        k = "acceptClaim by issuer" if cs(t["from"]) == iss else "acceptClaim by NON-issuer"
        out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k, "from": t["from"]}
    else:
        k = "other: to=" + to
        out[h + ":" + str(bid)] = {"bounty": bid, "claim": cid, "how": k, "from": t["from"]}
    c[k] += 1
for k, v in c.most_common(): print(v, k)
for key, o in out.items():
    if "NON" in o["how"] or "NOT" in o["how"] or "no submit" in o["how"] or o["how"].startswith("other"): print("FLAG", key, o)
json.dump(out, open(f"{bsdir}/accept_class.json", "w"), indent=0)
