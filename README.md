# kyanite-landing

Public Kyanite Labs landing site sources for [kyanitelabs.tech](https://kyanitelabs.tech).

**Who it is for:** operators of the public org landing surface.

**What you get:** landing site workspace (Python/static assets as present in-tree).

## Quick start

```bash
git clone https://github.com/KyaniteLabs/kyanite-landing.git
cd kyanite-landing
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
flask --app app run --port 3002
```

Then open <http://localhost:3002/>. `app.py` has no `__main__` entry point, so use `flask --app app run` locally; the container runs `gunicorn app:app` on port 3002 (see [`Dockerfile`](Dockerfile)). Optional integrations (Postgres, SMTP, Ko-fi, Telegram) are configured through environment variables read in `app.py`; database-backed features stay off unless the `ENABLE_*` flags are set.

## Docs

- Live site: [kyanitelabs.tech](https://kyanitelabs.tech)
- Sibling Pages surface: [kyanitelabs.github.io](https://github.com/KyaniteLabs/kyanitelabs.github.io) (private repository, maintainers only)
