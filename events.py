"""PoidhV2 event signatures (from the verified source) + decoder. All event params are non-indexed."""
from eth_abi import decode
from eth_utils import keccak, to_checksum_address
EVENTS = {
    "BountyCreated": ["uint256", "address", "string", "string", "uint256", "uint256"],
    "ClaimCreated": ["uint256", "address", "uint256", "address", "string", "string", "uint256"],
    "ClaimAccepted": ["uint256", "uint256", "address", "address", "uint256"],
    "BountyJoined": ["uint256", "address", "uint256"],
    "ClaimSubmittedForVote": ["uint256", "uint256"],
    "BountyCancelled": ["uint256", "address"],
    "ResetVotingPeriod": ["uint256"],
    "VoteClaim": ["address", "uint256", "uint256"],
    "WithdrawFromOpenBounty": ["uint256", "address", "uint256"],
}
TOPIC = {"0x" + keccak(text=f"{n}({','.join(t)})").hex(): n for n, t in EVENTS.items()}
TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()

def dec(log):
    t0 = log["topics"][0]
    if t0 in TOPIC:
        n = TOPIC[t0]
        vals = decode(EVENTS[n], bytes.fromhex(log["data"][2:]))
        vals = [to_checksum_address(v) if isinstance(v, str) and v.startswith("0x") and len(v) == 42 else v for v in vals]
        return n, vals
    if t0 == TRANSFER and len(log["topics"]) == 4:
        return "Transfer", [to_checksum_address("0x" + log["topics"][1][-40:]), to_checksum_address("0x" + log["topics"][2][-40:]), int(log["topics"][3], 16)]
    return None, None
