# kyanite-landing

Public Kyanite Labs landing site sources for [kyanitelabs.tech](https://kyanitelabs.tech).

**Who it is for:** operators shipping the public org landing surface (not a multi-tenant product app).

**What you get:** Flask app (`app.py`), templates/static assets, product pages under `products/`, Docker packaging, and tests.

## Quick start

```bash
git clone https://github.com/KyaniteLabs/kyanite-landing.git
cd kyanite-landing
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# or: docker compose up --build
```

## Docs

- Live site: [kyanitelabs.tech](https://kyanitelabs.tech)
- Sibling Pages surface: [kyanitelabs.github.io](https://github.com/KyaniteLabs/kyanitelabs.github.io)
- In-tree: `docs/`, `AGENTS.md`, `CONTRIBUTING.md`

## License

See [LICENSE](LICENSE).
