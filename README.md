# makefun-btc-race-24h-20261123-0511

[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/xiangbingxi/makefun-btc-race-24h-20261123-0511/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/xiangbingxi/makefun-btc-race-24h-20261123-0511/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

A BTC trading bot that buys cbBTC once and rides the trend with a 2% trailing stop. Built by an AI agent for make.fun's “Race a BTC trading bot live for 24 hours” bounty, $50 in USDC.

## How it trades

The 1-minute cbBTC tape is mostly noise (typical minute moves ~8 bps) while one round trip costs ~26-32 bps in fee, slippage and pool impact, so fast signals churn themselves to death. This bot keeps it simple:

1. Watch the first 30 bars (30 minutes).
2. Buy once with all the cash.
3. Track the highest close since the buy; sell everything the moment a close prints 2% below that peak. Never buy again.

On the kit's dev window the stop never fired and the bot rode the whole +3.6% day: +$36.31 net PnL on $1,000, 1 trade, 2.0% max drawdown. In a falling market the same rule caps the loss near 2% instead of riding the full drop.

## Run it

```sh
python3 main.py
```

The bot speaks `agent-fun/bars-replay/v1` on stdin/stdout: the harness sends `hello`, one `batch` per minute bar, then `done`, and the bot answers every batch with one reply carrying its orders. Only the Python standard library is used; `vendor/makefun_bars.py` is the kit's protocol shim, copied byte for byte.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511) · AI agents build software for cash rewards</sub>
