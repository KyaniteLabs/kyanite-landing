# Kyanite landing architecture

## Parts and flow

[app.py](app.py) is a large Flask module containing editorial inventories, rendering, public forms and optional commerce/content integrations. [agent_discovery.py](agent_discovery.py) is a separately registered public-discovery Blueprint. Templates and static scripts/assets supply the browser surface; [requirements.txt](requirements.txt) declares Flask/Gunicorn, requests, PostgreSQL driver and YAML support.

```text
browser -> proxy -> Flask -> template + in-module catalog/editorial data
                         -> static navigation/motion/sensorium/analytics
forms -> validation -> newsletter SQLite OR SMTP -> optional local JSONL fallback
webhooks / gated commerce -> optional PostgreSQL + external notification/payment APIs
agents -> discovery Blueprint -> cards/docs/Markdown + read-only RPC link guidance
```

[Dockerfile](Dockerfile) runs Gunicorn on port 3002. [docker-compose.yml](docker-compose.yml) declares loopback port binding, Traefik routing, read-only source mounts and persistent revenue storage; it is deployment intent, not a live-host receipt. Local Flask CLI works; despite older README wording, source also contains a `__main__` runner.

Newsletter SQLite is selected by `NEWSLETTER_DB_PATH`; its table stores subscriber/consent metadata and unsubscribe tokens. Subscription writes can succeed despite notification failure. Contact/intake email falls back to append-only JSONL when SMTP raises an OS error. PostgreSQL initialization is controlled by `ENABLE_SHOP_DB` / `ENABLE_CERAFICA_DB`; Cerafica route exposure additionally requires `ENABLE_CERAFICA_PUBLIC_API`. Importing the app calls these initialization functions, so test configuration must be isolated before import.

A process-local `PUBLIC_PAGE_CACHE` serves eligible successful GET representations; query-bearing, API, webhook and static paths are excluded. HTML/Markdown representations are keyed separately. ProxyFix trusts one forwarded hop. Security headers and body-size limits are set centrally; selected administrative routes pass through an environment-token gate.

## Risky paths and failure signatures

- **Public rendering/cache:** template/catalog drift, broken external links or stale process-local cached pages can coexist with HTTP 200. Multiple Gunicorn workers have separate caches. Match the actual browser rendering to the intended revision; the discovery health JSON alone says nothing about those paths.
- **Forms and privacy:** names, emails and project text can enter SQLite, email, local fallback logs and notifications. Local-log acceptance is not successful email delivery. Operators own access/retention/backup; do not place private submissions in public proof artifacts.
- **Admin/proxy:** absent admin token yields 404; incorrect token 403 on the selected protected paths. This is not proof every optional endpoint has equivalent authorization. ProxyFix assumes the deployment really enforces the trusted-hop boundary.
- **Newsletter:** unavailable persistent storage or invalid/missing consent yields errors. Unsubscribe links carry access-bearing tokens and can change state on GET; never use real subscriber links as a read-only probe. Public health does not test SQLite.
- **Commerce/webhooks:** missing Ko-fi token rejects requests; a valid callback can still return `ok: true, logged: false` after DB failure. Replay handling, price-to-product guessing, secret persistence in sales records, optional Cerafica authorization and outbound calls need separate security review. Source presence is not payment acceptance.
- **Discovery/analytics:** MCP/A2A handlers return bounded links rather than executing workflows; JSON-RPC errors need payload inspection. Browser PostHog/motion dependencies and remote resources are distinct from server-local data storage; do not promise offline/no-telemetry behavior for the website.

## Verification and rollback

An isolated virtualenv and database-disabled test client exercised twelve public GET routes and verified the unconfigured subscriber-admin path returns 404. No forms, payments, unsubscribes, SMTP deliveries or existing databases were exercised. Real browser captures are separate surface evidence, not all-path acceptance. Documentation changes alter no deployment or services; revert the docs commit for rollback and preserve operational data.
