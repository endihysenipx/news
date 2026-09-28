# Windows Server deployment

The deployment on `192.168.10.8` lives at `E:\websites\news-intelligence`.
It uses a dedicated PostgreSQL 18 database and role named `news_intel`, a
Python virtual environment in `.venv`, and a Next.js production build in
`frontend\.next`. Private settings are in the server's `.env` file.

Two scheduled tasks start the application at boot:

- `NewsIntelligenceAPI` runs `start-api.cmd` on `127.0.0.1:8001`.
- `NewsIntelligenceWeb` runs `start-web.cmd` on `127.0.0.1:3101`.

Cloudflare Tunnel publishes `news.primexeu.com` to `http://127.0.0.1:3101`.
The IIS site `News Intelligence` uses the `NewsIntelligencePool` application
pool and the same host binding on port 80 as an origin fallback. Its root is
`iis-proxy`, which proxies requests to the Next.js service. The other IIS
sites and PostgreSQL databases are separate.

Pushing to `main` runs `.github/workflows/deploy.yml` on GitHub Actions to
verify the frontend build and backend syntax. The server task
`NewsIntelligenceSync` checks the latest workflow result every five minutes.
When the successful run matches the current `main` commit, `sync.ps1` fetches
that commit and runs `deploy/deploy.ps1`. A failed workflow never deploys.

`deploy/deploy.ps1` builds the checkout in `_deploy\stage`, replaces only this
application's `backend`, `frontend`, and `.venv` directories, then checks the
API and web endpoints. It restores the previous directories if the health
check fails. The two latest backups stay in `_deploy\backups`. The production
`.env`, PostgreSQL database, `data` directory, IIS configuration, and
Cloudflare route are outside the replacement set.

Cloudflare Tunnel manages the public DNS record and HTTPS endpoint.
