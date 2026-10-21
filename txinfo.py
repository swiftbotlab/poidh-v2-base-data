import sys, json, time
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import rpc
rpc.CHAIN = sys.argv[1]
hs = sorted(set(h for f in sys.argv[3:] for h in [l["transactionHash"] for l in json.load(open(f))["result"]]))
out = {}
for s in range(0, len(hs), 20):
    res = rpc.batch([("eth_getTransactionByHash", [h]) for h in hs[s:s + 20]])
    for h, t in zip(hs[s:s + 20], res):
        out[h] = {"from": t["from"], "to": t["to"], "sel": t["input"][:10], "block": int(t["blockNumber"], 16), "value": int(t["value"], 16)}
    print(s + 20, "/", len(hs), file=sys.stderr, flush=True); time.sleep(0.4)
json.dump(out, open(sys.argv[2], "w"))
