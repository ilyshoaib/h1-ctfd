# bugbounty theme

A dark, modern bug-bounty-portal theme for [CTFd](https://github.com/CTFd/CTFd),
derived from CTFd's `core` theme (Bootstrap 5 + Alpine.js + Vite). Ships with a
prebuilt `static/` bundle so it works drop-in without a Node build.

Pairs with the **`bug_bounty`** plugin (see the repo root). The theme renders
fine on its own, but several touchpoints — hunter stats on profiles, the
report-status notification cards, live toasts — only light up when the plugin is
installed. All are guarded so nothing errors without it.

## Install

```
cp -r theme/bugbounty  /path/to/CTFd/CTFd/themes/bugbounty
```

Restart CTFd, then select it under **Admin → Config → Theme → `bugbounty`**.

## Rebuild (optional, for theme development)

The `assets/` folder holds the editable source; `static/` holds the compiled
output. To change styles/JS:

```
cd CTFd/themes/bugbounty
yarn install
yarn dev            # watch mode (stable filenames), or
yarn build          # one-time production build (hashed filenames)
```

CTFd caches the asset manifest in Redis. After a production rebuild, clear it
**without** wiping sessions:

```
redis-cli --scan --pattern 'flask_cache_*' | grep -v flask_cache_session | xargs redis-cli del
```

## Rebranding

Navbar/footer/watermark use HackerOne "h1" logo assets under `static/img/` and
`assets/img/`. Replace those files and the wordmark text in
`templates/components/navbar.html` and `templates/base.html` to rebrand.

## Credit

Based on the CTFd core theme, © CTFd LLC, Apache-2.0 (see `LICENSE`).
