# CTFd Bug Bounty

Turn [CTFd](https://github.com/CTFd/CTFd) into a **bug-bounty platform**: instead
of (or alongside) flag-based challenges, admins publish **targets** with scope,
hunters submit full **vulnerability reports** (title, description, steps, impact,
screenshot evidence, video link — all markdown), and admins **triage and award
points** that feed the normal CTFd scoreboard.

Two drop-in pieces, designed as a pair:

| Piece | Install into | What it is |
|-------|-------------|------------|
| `theme/bugbounty` | `CTFd/themes/bugbounty` | A dark, modern portal theme (derived from CTFd `core`). Prebuilt — no Node needed. |
| `plugins/bug_bounty` | `CTFd/plugins/bug_bounty` | A new `bug` challenge type + report submission, admin triage, awards, notifications. Self-contained. |

Both are **additive** — no CTFd core files are modified. The theme also works
without the plugin (bug-specific bits are guarded), and the plugin works with any
theme (it ships its own templates/assets), but together they're the full portal.

## Features

- **`bug` challenge type** — targets with in/out-of-scope and per-severity reward
  tiers (Low/Medium/High/Critical), created from the normal admin challenge UI.
- **Report submission** — title, description, steps to reproduce, impact,
  up-to-5 screenshot uploads, and a video URL. Full markdown (code blocks for
  payloads, etc.), server-side sanitized.
- **Admin triage page** — list + detail with review controls: severity, status,
  editable points, notes.
- **Statuses** — pending, triaging, accepted, rejected, duplicate, informative,
  **not applicable**, **spam**. Accepted **adds** points (as a CTFd Award);
  not-applicable/spam **deduct** points; changing status reconciles the award so
  scores never double-count.
- **Duplicate linking** — mark a report a duplicate of an earlier report id.
- **Discussion threads** — hunter ⇄ admin comments on each report.
- **Private notifications** — a per-hunter toast + a Notifications-center entry on
  every status change / reply (never broadcast to other users).
- **Hunter profile stats** — reports, accepted, acceptance rate, reputation,
  severity breakdown.

## Requirements

- A working CTFd instance (tested against the version this was built on —
  Bootstrap-5 `core`-theme era; the `_beta` asset pipeline).
- Redis + a database, per a normal CTFd deploy.
- The plugin auto-runs its own migrations on load (no manual DB steps).

## Install

```bash
# from your CTFd checkout root
cp -r /path/to/this-repo/theme/bugbounty    CTFd/themes/bugbounty
cp -r /path/to/this-repo/plugins/bug_bounty CTFd/plugins/bug_bounty

# restart CTFd (plugin migrations run automatically on startup)
docker compose restart ctfd     # or however you run CTFd
```

Then:

1. **Admin → Config → Theme →** select **`bugbounty`**.
2. **Admin → Challenges → +** → choose type **`bug`** → set name, scope, and the
   reward tiers.
3. Log in as a normal user → open the target → **Submit a Report**.
4. **Admin → plugins menu → Bug Reports** → open the report → set severity/status,
   award points, reply. Points appear on the scoreboard.

### Deploying from scratch?

`examples/` has a reference `docker-compose.yml`, a hardened `nginx.conf`
(serves only your domain, rejects direct-IP hits, Cloudflare real-IP), an
`.env.example`, and `scripts/backup.sh` (nightly DB + uploads backup). All use
placeholders — fill in your own secrets; **never commit your real `.env`**.

## Notes

- **Users vs teams:** bug bounty is naturally individual. The plugin works in
  both modes; in user mode it also redirects stale `/team(s)` links to the
  programs board.
- **Uploads:** evidence images go through CTFd's standard uploader; the plugin
  registers a `bug_report` file identity so the admin Files page stays happy.
- **Scoreboard:** points are granted purely via CTFd `Awards`, so the existing
  scoreboard/standings work unchanged.

## License

The theme derives from the CTFd core theme (© CTFd LLC, Apache-2.0). This
repository is distributed under Apache-2.0 — see [LICENSE](LICENSE).
