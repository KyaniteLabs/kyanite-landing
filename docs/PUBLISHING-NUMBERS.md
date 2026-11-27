# Publishing numbers: the 27B decode-rate claim (one-claim decision)

This document records **one decision about one published claim**. It is not a standard for
every model stack, and it must not be cited as one.

## The decision

Decided by Product on card `t_48dee2da` (2026-11-26; decision comment 13619): the
"59.7-64 tok/s cold" figure in the Qwen3.8-27B Strix Halo article either carries its
limitation in the same passage, or comes down. No replacement number is published.

Product's decision covered this claim only. **No program-wide decode-rate rule has been
decided.** A measurement standard for every model stack is the Chief Scientist's to set.
Nothing here states or implies one, and no seat may read this document as conferring that
authority. If such a standard is wanted, it belongs on a Chief Scientist card — and any
candidate would have to accept token-derived figures from a server's own timings, not only
`usage.completion_tokens`.

## The evidence behind this decision

PROVEN
- The published figure is a content-event rate, not a token rate. It came from
  `KyaniteLabs/qwen38-27b-strix-halo`, `components/bench/qwen27-bench.py`, which counts
  streamed content *events* and divides by elapsed seconds (`n / span`), then printed
  `tok/s`. Its own comment asserted `1 content chunk == 1 token`; that equality was never
  measured on that server, and the raw run output was never located.

NOT PROVEN
- That the magnitude is wrong. Two runs of the same 8-token output were reported as 0.7 and
  1.3 "tok/s" depending only on how many stream events arrived (audit 2026-11-08, ledger row
  31) — which is why the unit label could not stand. The magnitude may even be a floor
  rather than an overstatement. The stack is out of service, so re-measurement is not
  available, and no new number can be supported.

## Applying it to this claim

- The claim appears on several surfaces: the article body in both locales, its meta
  description, the magnet settings card, and the `llms.txt` / `llms-full.txt` output
  generated from the article body. On each of them, either qualify the figure in place so
  the limitation travels with the number in the same passage, or remove it. Do not
  substitute a new number that no instrument supports.
- The frontier comparison was removed as part of this fix: a comparison against an external
  figure is only like-for-like when that figure's unit is also verified. "Faster than X tok/s"
  where X's unit is unknown is not a claim this article makes.
- The article carries Simon's byline, so the wording change needs his one-word approval
  before it goes live.

## Record

- Product decision, this claim only: card `t_48dee2da`, 2026-11-26 (comment 13619).
- Instrument provenance: `KyaniteLabs/qwen38-27b-strix-halo`, `components/bench/qwen27-bench.py`.
- Superseded method transfer: card `t_d2fb0796` (done).
- Program-wide decode-rate standard: **NOT DECIDED.** Owner: the Chief Scientist seat. No
  card exists for it as of 2026-11-27.
