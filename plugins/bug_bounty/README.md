# bug_bounty plugin

Adds a `bug` challenge type to CTFd for running a bug-bounty program: hunters
submit vulnerability reports instead of flags; admins triage and award points.
Self-contained — registers a challenge type, a blueprint, templates/assets,
migrations (auto-run on load), a private notification store, hunter-stats Jinja
global, and a comment thread. No CTFd core files are modified.

Install: copy this folder to `CTFd/plugins/bug_bounty` and restart CTFd.
See the repository root README for the full feature list and admin flow.
Pairs with the `bugbounty` theme but works with any theme.
