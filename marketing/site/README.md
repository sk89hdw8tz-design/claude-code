# Site changes (theme files)

Source copies of theme files pushed to the unpublished theme
"Copy of Copy of Copy of Galveston Maps Co — 9-2…" (id 136828846287) on 2026-09-21.

- `sections/main-custom-map.liquid` — quote form: name, email, phone, and
  Galveston address all required; survey year select; optional note. Posts via
  Shopify's contact form, so submissions arrive at the store's sender email.
- `templates/page.custom-map.json` — page template wiring the section.
- `sections/header.liquid` — announcement bar removed; "Custom map of
  Galveston Island" button added next to Cart (and in the mobile drawer).
  Label and link are theme-editor settings.
- `custom-map-page.html` — fallback raw-HTML version of the form, not deployed.

Store objects created (theme-independent): page /pages/custom-map
(template suffix `custom-map`) and a "Custom Map" item in the main menu.

Publish the theme copy from Online Store → Themes to take it live.
