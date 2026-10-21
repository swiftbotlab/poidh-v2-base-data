#!/usr/bin/env python3
"""Dump poidh v2 contract state at one pinned block: bounties, claims, participants, NFT owners.
Usage: fetch_state.py base|arbitrum OUT.json [BLOCK]. Read-only eth_call over public RPCs, no keys."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import rpc
from eth_abi import encode, decode
from eth_utils import keccak, to_checksum_address

CONTRACTS = {"base": ("0xb502c5856f7244dccdd0264a541cc25675353d39", "0xddfb1a53e7b73dba09f79fca24765c593d447a80"),
             "arbitrum": ("0x0aa50ce0d724cc28f8f7af4630c32377b4d5c27d", "0xddfb1a53e7b73dba09f79fca24765c593d447a80")}
chain, out = sys.argv[1], sys.argv[2]
rpc.CHAIN = chain
C, N = CONTRACTS[chain]
BLOCK = int(sys.argv[3]) if len(sys.argv) > 3 else int(rpc.call("eth_blockNumber", []), 16) - 20
TAG = hex(BLOCK)
def sel(s): return "0x" + keccak(text=s)[:4].hex()
MC3 = "0xcA11bde05977b3631167028862bE2a173976CA11"  # Multicall3 (same address on Base and Arbitrum)
def calls(to, sig, argtypes, argss, chunk=80):
    """Many view calls via Multicall3.aggregate3 (allowFailure) at the pinned block; failed sub-calls -> None."""
    res = []
    datas = [bytes.fromhex(sel(sig)[2:]) + encode(argtypes, a) for a in argss]
    groups = [datas[s:s + chunk] for s in range(0, len(datas), chunk)]
    for g0 in range(0, len(groups), 4):
        reqs = []
        for g in groups[g0:g0 + 4]:
            cd = sel("aggregate3((address,bool,bytes)[])") + encode(["(address,bool,bytes)[]"], [[(to, True, d) for d in g]]).hex()
            reqs.append(("eth_call", [{"to": MC3, "data": cd}, TAG]))
        for r in rpc.batch(reqs):
            for ok, data in decode(["(bool,bytes)[]"], bytes.fromhex(r[2:]))[0]:
                res.append("0x" + data.hex() if ok else None)
        print(sig, len(res), "/", len(argss), file=sys.stderr, flush=True)
    assert len(res) == len(argss)
    return res
def u(r): return int(r, 16)

nb = u(calls(C, "bountyCounter()", [], [[]])[0]); nc = u(calls(C, "claimCounter()", [], [[]])[0])
supply = u(calls(N, "totalSupply()", [], [[]])[0])
blk = rpc.call("eth_getBlockByNumber", [TAG, False])
print("block", BLOCK, "bounties", nb, "claims", nc, "nft supply", supply, file=sys.stderr)
BT = ["uint256", "address", "string", "string", "uint256", "address", "uint256", "uint256"]
bounties = []
for i, r in enumerate(calls(C, "bounties(uint256)", ["uint256"], [[i] for i in range(nb)])):
    v = decode(BT, bytes.fromhex(r[2:]))
    assert v[0] == i
    bounties.append({"id": i, "issuer": to_checksum_address(v[1]), "name": v[2][:120], "amount": str(v[4]), "claimer": to_checksum_address(v[5]), "createdAt": v[6], "claimId": v[7]})
for i, r in enumerate(calls(C, "getParticipants(uint256)", ["uint256"], [[i] for i in range(nb)])):
    ps, am = decode(["address[]", "uint256[]"], bytes.fromhex(r[2:]))
    bounties[i]["participants"] = [[to_checksum_address(p), str(a)] for p, a in zip(ps, am)]
CT = ["uint256", "address", "uint256", "address", "string", "string", "uint256", "bool"]
claims = []
for i, r in enumerate(calls(C, "claims(uint256)", ["uint256"], [[i] for i in range(nc)])):
    v = decode(CT, bytes.fromhex(r[2:]))
    claims.append({"id": v[0], "slot": i, "issuer": to_checksum_address(v[1]), "bountyId": v[2], "bountyIssuer": to_checksum_address(v[3]), "name": v[4][:80], "createdAt": v[6], "accepted": v[7]})
tids = [u(r) for r in calls(N, "tokenByIndex(uint256)", ["uint256"], [[i] for i in range(supply)])]
owners = {}
for t, r in zip(tids, calls(N, "ownerOf(uint256)", ["uint256"], [[t] for t in tids])):
    owners[str(t)] = to_checksum_address("0x" + r[-40:])
json.dump({"chain": chain, "contract": C, "nft": N, "block": BLOCK, "block_time": u(blk["timestamp"]), "bounties": bounties, "claims": claims,
           "nft_supply": supply, "owners": owners}, open(out, "w"))
print("wrote", out, file=sys.stderr)
