# KyaniteLabs landing and shop

The Flask-backed public front door at kyanitelabs.tech: discover KyaniteLabs projects, read build notes, find implementation help, and choose a next step. Unlike the sibling GitHub Pages repository, this app also owns forms and optional operational integrations.

## Core experience and existing surfaces

Visitors browse English/Spanish home, about, project listings, blog, implementation offer/intake, shop/tip/product pages and free reference worksheets. Newsletter signup requires explicit consent; contact/intake collect requests, not automatic delivery commitments. External purchase/support links do not make this site a complete commerce platform.

The current [app.py](app.py) inventory contains 16 public-project records, two product records, 28 base blog posts and five lead-magnet records, with additional Spanish copy/variants. These are editorial/catalog content, not reference datasets or evidence that every linked product works. [products](products/) includes the AI coding-agent blueprint and Claude Code productivity pack source documents; templates/static assets include project art, brand material, motion/navigation helpers and the Liminal sensorium layer.

Existing server features include newsletter subscription/unsubscription and protected export, contact/intake email with local-log fallback, Ko-fi webhook/sales integration code, and gated Cerafica commerce/content endpoints. Optional PostgreSQL features are off by default. Presence of checkout/webhook code is not proof a payment path is live or safe.

[agent_discovery.py](agent_discovery.py) adds API/OpenAPI, well-known cards/catalog/skill, HTML-to-Markdown negotiation, and read-only MCP/A2A documentation routing. These guide agents to public resources and human-approved intake; they do not provision credentials, submit forms or implement the listed products.

## Limits and proof

Readiness depends on storage, SMTP and explicitly configured integrations. A contact response may say `delivery: local_log` rather than email; subscription persistence and notification delivery are separate. Public API health is static service discovery, not a database/payment/email health check.

Source inspection and a read-only local Flask route probe establish a bounded rendering/discovery path only. Real signup, email, purchase, admin and private-data paths require separate approved operator-side proof. These docs do not authorize submissions, deploy the site, or alter data.
