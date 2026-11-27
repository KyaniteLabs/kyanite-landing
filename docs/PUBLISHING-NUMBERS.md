# Publishing numbers: the decode-rate rule

Effective 2026-11-26 (Product ruling, carried into the site repo by Growth on card `t_48dee2da`).

## The rule

No decode-rate figure for any model stack is published unless it is **usage-derived**:
`usage.completion_tokens` from the server divided by the generation window. The raw run
output must be attached or linked next to the number.

Event or chunk rates may appear only labelled as what they are — a stream-event rate — and
must never be written as `tok/s` without that qualifier in the same passage.

## Why

The Qwen3.8-27B Strix Halo article published "59.7-64 tok/s cold" from
`qwen38-27b-strix-halo/components/bench/qwen27-bench.py`, which counts streamed content
*events* and divides by elapsed seconds (`n / span`), then printed `tok/s`. Its own comment
asserted `1 content chunk == 1 token`; that equality was never measured on that server, and
the raw run output was never located. Two runs of the same 8-token output were reported as
0.7 and 1.3 "tok/s" depending only on how many stream events arrived (audit 2026-11-08,
ledger row 31). The magnitude may even be a floor rather than an overstatement — the point
is that the **unit was never proven**, so the number could not honestly carry a token label.

## Applying it

- When a figure fails this rule, either qualify it in place so the limitation travels with
  the number in the same passage, or remove the figure. Do not substitute a new number that
  no instrument supports.
- A comparison against an external figure is only like-for-like when that figure's unit is
  also verified. "Faster than X tok/s" where X's unit is unknown is not a claim we make.
- Applies to article bodies, meta descriptions, summaries, tables, magnet pages, `llms.txt`
  / `llms-full.txt` output, decks and READMEs — every surface a reader meets the number.
  Both locales.
- Bylined articles: the wording change needs the byline owner's approval before it goes live.

## Record

- Product decision: card `t_48dee2da`, 2026-11-26.
- Instrument provenance: `KyaniteLabs/qwen38-27b-strix-halo`, `components/bench/qwen27-bench.py`.
- Superseded method transfer: card `t_d2fb0796` (done).
