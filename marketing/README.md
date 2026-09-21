# Galveston Maps Co. — Marketing Operating System

Store: https://www.galvestonmaps.co (Shopify, Basic plan)
Products: Galveston 1899, Galveston 1912, The Pair (1899 & 1912). $495–$1,450.

This folder is the single source of truth for how marketing runs. Nothing in
here sends an email or spends a dollar on its own. Every campaign passes
through the approval gate in `budget.yaml` before it runs.

## How the loop works

1. **Monday brief (automated).** A scheduled Claude Routine pulls the last
   7 days of Shopify analytics (sessions, referrers, cart adds, checkouts,
   orders, subscriber count), compares them to the KPI thresholds in
   `kpis.yaml`, and writes a campaign proposal to `briefs/YYYY-MM-DD.md`.
   The brief names the channel, the template, the audience, the exact spend,
   and the expected result.
2. **Approval gate (you).** You reply APPROVE, EDIT, or SKIP. Nothing runs
   until you approve. If you approve with a spend, it has to fit inside the
   caps in `budget.yaml`.
3. **Execution.** On approval, Claude does everything it can reach through
   the Shopify connection (discount codes, segments, product copy, landing
   text) and hands you a paste-ready package for anything it cannot send
   directly (Shopify Email sends, Meta / Google ad uploads). See "What can
   run without you" below.
4. **Readout.** The following Monday's brief opens with results of the last
   campaign against its expected result, and adjusts.

## What can run without you (once approved)

| Action | Can Claude execute it? | Notes |
|---|---|---|
| Discount codes | Yes | Shopify Admin API |
| Customer segments | Yes | Shopify Admin API |
| Product / collection copy, tags, images | Yes | Shopify Admin API |
| Store pages (About, Story of the Storm) | Yes | Shopify Admin API |
| Shopify Email campaign send | No (paste-ready draft only) | Shopify Email has no public send API. Klaviyo does; connecting it would close this gap. |
| Meta / Google / Pinterest ad launch | No (paste-ready ad set only) | Needs an ad account connector. Once connected, launch can run on approval. |
| Budget spend | Never without approval | Hard caps in `budget.yaml` |

## Files

- `budget.yaml` — monthly cap, per-campaign cap, approval flags.
- `kpis.yaml` — the numbers that trigger which play.
- `playbook.md` — the campaign calendar and which template runs when.
- `templates/email/` — welcome, launch, storm story, abandoned cart, gift season.
- `templates/ads/` — Meta / Instagram, Google Search, Pinterest.
- `briefs/` — one file per weekly proposal, with your decision recorded.
