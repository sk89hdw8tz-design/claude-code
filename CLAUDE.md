# Standing permissions for Galveston Maps Co. image protection work

- Allowed without asking: edit unpublished themes; create new theme copies; create or edit draft pages,
  metaobjects and theme settings; delete Shopify Files confirmed unreferenced by an inventory pass
  (log the list on the dashboard first); re-run model reviews; update the dashboard and reports.
- Always ask first: publishing or deleting a theme; deleting product media or lifestyle photos;
  anything that spends money; Terms of Service or legal text; DNS or domain changes.
- Never touch: prices, orders, customers, discounts, policies, the live theme.
- Dashboard: https://claude.ai/artifact/EuiEASUh8F1sRxTJq6EKzY

## Context for a fresh session

- The site is the Shopify store Galveston Maps Co. (www.galvestonmaps.co), Basic plan, custom "Strand" theme.
- Phase 1 (canvas-only viewer, loupe, visit mark, pan panels, QR landing pages) lives on the unpublished theme
  "Image Guard staging — 10-14-2026 (do not publish yet)", id gid://shopify/OnlineStoreTheme/137061957839.
- Phase 2 (Cloudflare Worker + R2 tile service) starts once CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are
  stored as environment secrets and cdn.shopify.com, api.cloudflare.com, *.workers.dev and
  www.galvestonmaps.co are allowed in the environment's network access.
- Read the dashboard's findings, decisions and log before acting; the reviewers' reports are linked from the handoff.
