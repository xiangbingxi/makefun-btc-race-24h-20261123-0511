"""BTC trend rider for make.fun bars-replay/v1.

Idea (mine, tuned on the kit's dev window): the 1-minute cbBTC/USDC tape is
mostly noise -- 1-minute closes move about 8 bps in a typical minute, while
one full round trip costs about 26-32 bps in fee, slippage and pool impact.
Fast signals (EMA crosses, breakouts) churned themselves to death on the dev
window: every one of them finished below buy-and-hold once fees were counted.

So this bot does the simplest thing that survives fees:

1. Warm up for 30 bars (30 minutes), just watching closes go by.
2. Buy once, with all of the cash, at the next bar's open.
3. Then hold and defend: track the highest close seen since the buy, and
   sell everything the moment a close prints 2% below that peak. The sale
   fills at the next bar's open. Never buy again. Once the stop triggers, the
   bot latches into liquidation and keeps sending the sell every batch until
   the position is flat, even if the price bounces back above the trigger or
   a fill is rejected: a rejected sell never cancels the exit.

Why it works: a 2% trailing stop is far outside the minute-to-minute noise,
so it almost never fires on chop -- on the dev window it never fired at all
and the bot rode the whole +3.6% day. When the market really turns down it
issues the sell the moment a close prints 2% below the highest close seen
since the buy. That 2% is the trigger, not a loss cap: the peak starts from
the first close after the position opens, the fill comes at the next bar's
open, and a gap past the 500 bps slippage cap can reject the sell outright
-- while a bot that just holds rides the full drop. In a flat market it
behaves like buy-and-hold; in a bear market it steps aside early; in a bull
market it stays in. It makes 1-2 trades per 24-hour window, so fees stay tiny.

Everything here is integer arithmetic on the closes the harness sends, so
two runs on the same bars produce the same orders byte for byte: no clock,
no randomness, no environment, no files outside the repository.

Protocol notes (agent-fun/bars-replay/v1, via the vendored shim):
- the harness sends hello once, then one batch per minute, then done;
- a batch carries the bar that just closed, the fills of the orders sent on
  the previous batch, and the account (cash and positions);
- the bot answers every batch with exactly one reply echoing its seq, with
  its orders for the next bar;
- orders decided on a batch fill at the next bar's open, so a buy decided
  here shows up as a position in the next batch, and a sell decided here
  clears the position in the next batch;
- a buy spends quote units (USDC micro-units), a sell names a quantity of
  CBBTC; max_slippage_bps bounds the fill against the latest close.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars
SYMBOL = "CBBTC"

# Bars to watch before the first (and only) buy: 30 minutes is short enough
# to catch a rally that starts early, long enough to have a real peak to
# trail from once the position is open.
WARMUP_BARS = 30

# Sell everything once a close prints this far below the highest close seen
# since the buy, in basis points (200 = 2%).
TRAIL_BPS = 200

# Fills are bounded against the latest close; a 1-minute move over 5% is far
# outside anything the dev window shows (largest was under 1%), so this cap
# almost never binds -- it only guards against a wild gap.
MAX_SLIPPAGE_BPS = 500

# A buy that is rejected (slippage, or a missing bar at the fill open) is
# retried on the next batch, at most this many times in total.
MAX_BUY_ATTEMPTS = 3

# A buy must be worth at least 1 USDC; the bot always buys with all its cash,
# so this is only a safety check.
MIN_NOTIONAL_QUOTE_UNITS = 1_000_000

BPS = 10_000


class TrendRider:
    """One position, one trailing stop. All state is plain ints and bools."""

    def __init__(self):
        self.bars_seen = 0
        self.peak = None          # highest close seen while holding, else None
        self.was_holding = False  # held a position on the previous batch
        self.exited = False       # a sell has filled: never buy again
        self.liquidating = False  # stop triggered: keep selling until flat
        self.buy_attempts = 0

    def on_batch(self, state, batch):
        bar = state.latest.get(SYMBOL)
        if bar is None:
            return []
        close = int(bar["c"])
        self.bars_seen += 1

        holding = state.positions.get(SYMBOL)
        qty = holding.qty if holding is not None else 0

        if qty > 0:
            self.was_holding = True
            if self.peak is None or close > self.peak:
                self.peak = close
            # The stop latches: once triggered, keep selling every batch
            # until the position is flat. A fill can be rejected (no bar at
            # the fill open, or the fill slipping past max_slippage_bps), and
            # the price can bounce back above the trigger while the rejection
            # is reported -- either way the exit stands, so re-checking the
            # price alone would silently drop the stop and keep holding.
            # <= so a close exactly 2% below the peak triggers too.
            if self.liquidating or close * BPS <= self.peak * (BPS - TRAIL_BPS):
                self.liquidating = True
                print(f"[{state.seq}] sell all {qty} at close {close} "
                      f"(peak {self.peak})", file=sys.stderr)
                return [{
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        # Not holding. A sell filled if we held on the previous batch.
        if self.was_holding:
            self.was_holding = False
            self.exited = True
            self.liquidating = False
            self.peak = None
            return []

        if self.exited:
            return []
        if state.warming_up:
            return []
        if self.bars_seen < WARMUP_BARS:
            return []
        if self.buy_attempts >= MAX_BUY_ATTEMPTS:
            return []
        # A buy sent on the previous batch resolves at this bar's open, and
        # this batch already carries its fill (or rejection) and the account
        # after it: if it filled, the position shows above and we never get
        # here; if it was rejected, the cash is untouched and the position
        # is empty, so the retry goes out on this very batch -- no extra bar
        # of waiting. A duplicate buy is impossible: a buy is only sent
        # when no position is held and the previous buy's outcome is known.
        if state.cash < MIN_NOTIONAL_QUOTE_UNITS:
            return []
        self.buy_attempts += 1
        print(f"[{state.seq}] buy all cash {state.cash} at close {close}",
              file=sys.stderr)
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": state.cash,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]


def main():
    makefun_bars.run(TrendRider().on_batch)


if __name__ == "__main__":
    main()
