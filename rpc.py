"""Tiny read-only JSON-RPC helper (no keys). Rotates over public endpoints; batch items that revert come back as None."""
import json, sys, time, urllib.request
RPCS = {"base": ["https://mainnet.base.org", "https://base.drpc.org"],
        "arbitrum": ["https://arb1.arbitrum.io/rpc", "https://arbitrum.drpc.org", "https://arbitrum-one-rpc.publicnode.com"]}
CHAIN = "base"
UA = {"Content-Type": "application/json", "User-Agent": "poidh-v2-data"}
_i = [0]

def post(body, rpc=None):
    for attempt in range(8):
        url = rpc or RPCS[CHAIN][_i[0] % len(RPCS[CHAIN])]
        try:
            r = urllib.request.Request(url, data=json.dumps(body).encode(), headers=UA)
            return json.load(urllib.request.urlopen(r, timeout=90))
        except Exception as e:
            print("rpc retry", attempt, url, str(e)[:100], file=sys.stderr, flush=True)
            _i[0] += 1
            time.sleep(1 + attempt * 3)
    raise SystemExit("rpc failed")

def call(method, params, rpc=None):
    out = post({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, rpc)
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error']}")
    return out["result"]

def batch(reqs, rpc=None):
    """reqs: list of (method, params). Returns results in order; 'execution reverted' items -> None."""
    body = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(reqs)]
    for attempt in range(8):
        out = post(body, rpc)
        if isinstance(out, dict) or len(out) != len(body):
            print("batch err", str(out)[:200], file=sys.stderr); _i[0] += 1; time.sleep(2 + attempt * 3); continue
        out = sorted(out, key=lambda x: x["id"])
        bad = [o["error"] for o in out if "error" in o and "revert" not in str(o["error"]).lower()]
        if bad:
            print("batch item err", bad[:2], file=sys.stderr); _i[0] += 1; time.sleep(2 + attempt * 3); continue
        return [o.get("result") for o in out]
    raise SystemExit("batch failed")
