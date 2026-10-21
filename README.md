# poidh v2 data: ETH paid out, ETH earned and NFTs held per wallet (exploit-excluded)

Answers to the poidh "poidh Base v2 data" and "poidh Arbitrum v2 data" bounties ([Arbitrum section](#arbitrum)). One row per wallet, read straight from chain state and the contract's
own events. No indexer, no API keys.

## Base

**CSV:** [`poidh_v2_base_wallets.csv`](poidh_v2_base_wallets.csv) (2,070 wallets) · summary: [`summary_base.json`](summary_base.json) · preview: [`preview_base.png`](preview_base.png)

- Main contract `PoidhV2` [`0xb502c5856f7244dccdd0264a541cc25675353d39`](https://basescan.org/address/0xb502c5856f7244dccdd0264a541cc25675353d39) (verified source on Sourcify)
- NFT contract `POIDH V2` [`0xddfb1a53e7b73dba09f79fca24765c593d447a80`](https://basescan.org/address/0xddfb1a53e7b73dba09f79fca24765c593d447a80)
- **Snapshot: Base block 52914329** (2026-10-21 21:26 UTC). All state reads are `eth_call` pinned to that block.

| | |
|---|---|
| bounties | 990 (532 completed on-chain, 257 cancelled, 201 open) |
| legit completions | **495** |
| completions excluded as exploit | **37** (0.180285 ETH gross) in 3 transactions |
| total ETH paid out = total ETH earned | **3.980363457911831783 ETH** (gross, before the 2.5% fee) |
| NFTs minted (`totalSupply`) | 5,320 = 495 legit in wallets + 4,785 legit held by the protocol contract + 40 exploit-minted (37 in victims' wallets, 3 in the contract) |

### Columns

| column | meaning |
|---|---|
| `address` | checksummed wallet: every bounty issuer, every contributor to an open bounty (including ones who withdrew), every claim submitter and every current NFT holder. The protocol contract itself is **not** a row (see the NFT line above). |
| `eth_paid_out` | ETH this wallet contributed to bounties that were **legitimately completed**. Solo bounty: the issuer's full amount. Open (crowdfunded) bounty: each contributor's own share, from the contract's `participants` / `participantAmounts` (withdrawn shares are 0 there). Per bounty the shares sum exactly to the paid amount (asserted). Cancelled and open bounties count 0. |
| `eth_earned` | gross bounty amount this wallet won on legitimately completed bounties (`bounty.amount`, i.e. before the 2.5% protocol fee). |
| `nfts_held` | legitimate poidh v2 claim NFTs this wallet holds at the snapshot (`tokenByIndex` + `ownerOf` over all 5,320 tokens), exploit-minted "Exploit"/"x" NFTs excluded. |
| `bounties_funded_completed`, `bounties_won` | counts behind the two ETH columns |
| `exploit_nfts_held` | exploit-minted NFTs sitting in this wallet (they were pushed to the victims' wallets by the exploit's `acceptClaim`); not counted in `nfts_held` |
| `note` | labels for attacker and whitehat contracts (all zeros) |

Checks (asserted in `build_csv.py`): sum `eth_paid_out` == sum `eth_earned`; every completed bounty has exactly one
`ClaimAccepted` event (532 events = 532 completed bounties); NFTs in wallets + in the contract == `totalSupply`.
Amounts are summed in integer wei and printed with `Decimal` (no float rounding).

### How completion and legitimacy were decided

From the verified source: `acceptClaim`/`resolveVote` set `bounty.claimer` to the claim's author; `cancelSoloBounty` and
`cancelOpenBounty` set `bounty.claimer = issuer`. So completed = `claimer != 0x0 && claimer != issuer`.

Then **every one of the 532 `ClaimAccepted` events** was traced back to the transaction that produced it and classified by
who triggered it (`classify.py`, results in `summary_base.json -> how_accepted`):

- 324 `acceptClaim` sent directly by the bounty issuer, 4 by the issuer's ERC-4337 smart wallet
- 167 `resolveVote` after a vote the **issuer** opened with `submitClaimForVote` (157 + 6 opened via smart wallet + 4 resolved through a smart wallet)
- **37 inside contract-creation transactions by unrelated EOAs = the exploit.** Excluded.

### The exploit (identified on-chain)

The flaw (post-mortem: https://words.poidh.xyz/poidh-december-8th-exploit): in `acceptClaim`, when an open bounty has
more than one participant slot but every slot after the first is `address(0)` (all joiners withdrew), the
`msg.sender == issuer` check is skipped. The attacker created a claim, joined the bounty with 1 wei, withdrew it (leaving
a zeroed slot), and accepted its own claim, receiving 97.5% of the bounty. This hits every open bounty with a single
remaining contributor.

| tx | when | what | bounties |
|---|---|---|---|
| [`0x0545a4e5...4422f11f`](https://basescan.org/tx/0x0545a4e5800632ba2194fb9349264ff7f3d3bb18d28ee168d57369b14422f11f) | 2025-12-08 19:46:37 UTC, block 39216925 | EOA `0xc9cade0aa7bd77b00d1ab057a3684c698725cf54` deploys a contract; attacker contract `0xCb18f71e12b85058974f181E8cCA769AB5eEDbbd` makes 36 "Exploit / Give me money" claims (ids 5275-5310), 33 accepted (3, on bounties 95-97, were not) | 50, 59, 247, 460, 534, 566, 576, 668, 687, 732, 736, 737, 739, 741, 742, 744, 746, 748, 793, 812, 817, 833, 835, 872, 873, 874, 875, 876, 924, 931, 960, 969, 976 |
| [`0xc2909180...be2539c4`](https://basescan.org/tx/0xc29091802e4e95eafe0b8b3be53736ccce6dab6928fc978b5876c6c9be2539c4) | 2025-12-08 ~19:59 UTC, block 39217321 | same EOA, attacker contract `0xdcF35d067384b30e95711B1893Fb767B63c5a4A8`, claims 5312-5314 on bounties whose other contributors had withdrawn | 124, 698, 731 |
| [`0xa5f6a492...4c202a38`](https://basescan.org/tx/0xa5f6a49223b7c46d7b383307d16cdb76cf3acaa24b92532927025b564c202a38) | 2026-07-22, block 48966377 | EOA `0x93934039b6a4ba1aadf6f5113c239e757c9c2ab3`, contract `0x0dA89b38005472c31B38b94ABED992f431a71276`: same flaw, claim 5319 "x" accepted on old bounty 450 (paid from bounty 989's deposit, the only ETH then left in the contract) | 450 |

Those 37 completions are excluded from `eth_paid_out` (the victims' deposits were stolen, not paid out) and from
`eth_earned` (the attacker contracts show 0). Their 40 claim NFTs are excluded from `nfts_held` and shown in
`exploit_nfts_held`. Full list with per-tx bounty ids: `exploit_base.json` and `summary_base.json`.

**Whitehat rescue (not counted):** [`0xdd1cb64c...8b1178b3`](https://basescan.org/tx/0xdd1cb64cded3abcd5078773d7d6075780674c052a83a3d22b9c7f9538b1178b3)
(2025-12-09 02:27 UTC, block 39228940, from `0x110e34a24693910ebbc28350893ecd0e149309d6`). Its contract
`0x02e9126AfC799484dB82546fc0289b31738ec2af` opened bounty 985 with 0.0001 ETH; helper
`0xe0C276F08Af61F33CA4F0DE68485994eed79A1ef` joined with 0.58175 ETH and withdrew inside `cancelOpenBounty`'s refund loop,
so the loop refunded that share twice and emptied the contract. Bounty 985 ends **cancelled**, so it adds nothing to
paid out or earned. **User refunds** after the incident were plain ETH transfers from the team, outside the contract; the
open bounties they covered stay "open" on-chain and count 0. Legit activity on Dec 8 itself (bounties 982-984, claims
5274, 5311, 5315) is kept; only the transactions above are excluded.

### Re-run (Base)

```
python3 fetch_state.py base state_base.json 52914329      # bounties, participants, claims, NFT owners (Multicall3, pinned block)
python3 fetch_events.py base bs/                          # ClaimAccepted / vote / join ... events (Blockscout logs API)
python3 txinfo.py base bs/txinfo.json bs/acc.json bs/vote.json bs/voteclaim.json bs/reset.json bs/cancel.json bs/withdraw.json
python3 classify.py base state_base.json bs 0xb502c5856f7244dccdd0264a541cc25675353d39
python3 build_csv.py state_base.json bs/accept_class.json bs/join.json poidh_v2_base_wallets.csv summary_base.json exploit_base.json
```
Needs `eth-abi` and `eth-utils`. Public RPCs: mainnet.base.org, base.drpc.org.

## Arbitrum

**CSV:** [`poidh_v2_arbitrum_wallets.csv`](poidh_v2_arbitrum_wallets.csv) (247 wallets) · summary: [`summary_arbitrum.json`](summary_arbitrum.json) · preview: [`preview_arbitrum.png`](preview_arbitrum.png)

- Main contract `PoidhV2` [`0x0aa50ce0d724cc28f8f7af4630c32377b4d5c27d`](https://arbiscan.io/address/0x0aa50ce0d724cc28f8f7af4630c32377b4d5c27d) (verified on Sourcify; contract body byte-identical to the Base source, so the same flaws exist)
- NFT contract `POIDH V2` [`0xddfb1a53e7b73dba09f79fca24765c593d447a80`](https://arbiscan.io/address/0xddfb1a53e7b73dba09f79fca24765c593d447a80) (same address as on Base)
- **Snapshot: Arbitrum One block 517036925** (2026-10-21 21:41 UTC), all reads pinned to it. Same columns, same method, same checks as Base.

| | |
|---|---|
| bounties | 180 (112 completed, 44 cancelled, 24 open) |
| legit completions | **112** (all of them) |
| total ETH paid out = total ETH earned | **0.31808279 ETH** (gross) |
| NFTs minted (`totalSupply`) | 437 = 112 in wallets + 325 held by the protocol contract (pending claims on open/cancelled bounties) |

**Did the Dec 8 exploit touch Arbitrum? No.** All 112 `ClaimAccepted` events were traced: 102 `acceptClaim` sent by the
bounty issuer, 10 `resolveVote` after a vote the issuer opened (1 resolved through a smart wallet). No contract-creation
or third-party acceptances, no "Exploit" claims; the claims created around Dec 8 (ids 426-434) are ordinary user claims
and none was accepted. Nothing is excluded from the totals.

**Whitehat rescue (not counted):** [`0x6b5393a6...0f7e24`](https://arbiscan.io/tx/0x6b5393a6952436d933ebf63b0c8427a708d2b1182c6a371ec38e6149aa0f7e24)
(2025-12-09 02:27:33 UTC, block 408671204, from `0x110e34a24693910ebbc28350893ecd0e149309d6`): same rescue contract
`0x02e9126AfC799484dB82546fc0289b31738ec2af` opened bounty 179 (0.0001 ETH), helper `0xe0C276F08Af61F33CA4F0DE68485994eed79A1ef`
joined with 0.02485801 ETH and withdrew inside `cancelOpenBounty`'s refund loop. Bounty 179 ends **cancelled**, so it adds
nothing. User refunds were sent outside the contract and are not counted; the refunded bounties stay "open" on-chain.
Details: `exploit_arbitrum.json`.

Re-run: the same five commands with `arbitrum`, `state_arb.json`, `bs_arb/` and contract
`0x0aa50ce0d724cc28f8f7af4630c32377b4d5c27d` (public RPCs: arb1.arbitrum.io, arbitrum.drpc.org).
