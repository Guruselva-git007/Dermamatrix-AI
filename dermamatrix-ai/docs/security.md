# Local prototype security posture

DermaMatrix AI is a local final-year-project prototype, not a production
health-service security implementation. This document records what the
repository actually enforces and what remains required before deployment.

## Implemented controls

- Account passwords are persisted only as salted Werkzeug password hashes.
- Flask uses signed, HTTP-only, `SameSite=Lax` session cookies. The cookie is
  marked `Secure` only when `FLASK_SESSION_SECURE=true` behind HTTPS.
- Explicit `DERMAMATRIX_ENV=production` fails startup unless
  `FLASK_SECRET_KEY` is persistent, at least 32 characters and not an obvious
  configured placeholder, and `FLASK_SESSION_SECURE=true`. This prerequisite
  does not measure secret entropy or verify HTTPS/proxy infrastructure; local
  mode retains its existing HTTP and temporary-secret behavior.
- Authenticated records are resolved from the server-side session; browser
  request bodies cannot select another user's profile, assessment, routine,
  report, or history export.
- Local requests must use `localhost`, `127.0.0.1` or `::1`; arbitrary Host
  values are rejected before routes, including DNS-rebinding hostnames.
  Explicit production mode requires configured `DERMAMATRIX_TRUSTED_ORIGINS`
  and an exact request-origin match; it does not guess a public URL.
- Unsafe API requests (POST/PUT/PATCH/DELETE, including registration, login
  and logout) validate a supplied Origin against the actual request origin.
  If Origin is absent, a supplied full Referer URL is checked by origin.
  Browser `Sec-Fetch-Site`, when present, must be `same-origin`.
  The existing GET assessment-PDF endpoint and its automatic HEAD method also
  check Origin/Referer and
  rejects cross-site/same-site fetch metadata because generating it updates
  report-ledger metadata. Direct `none` navigation remains permitted there.
  Rejection precedes database access and application image reads/decoding.
- Uploaded images are limited to 10 MB, decoded from their actual bytes rather
  than a supplied MIME type, required to match their extension, and capped at
  16 megapixels before RGB conversion or model processing. Truncated,
  unsupported, and decompression-bomb images are rejected.
- Image pixels and visual overlays are processed in memory and are not stored
  with assessments or reports.
- API and local asset responses are marked `Cache-Control: no-store`.
- The app sends `nosniff`, frame-denial, same-origin referrer, restricted
  permissions, and same-origin resource-policy headers.
- Local secrets and model/data artifacts are excluded from Git.
- Interface fonts are self-hosted with the original font families and OFL
  notices; page entry no longer needs a Google Fonts request. Optional maps,
  product and pharmacy links remain explicit external navigation.

## Deliberate local limitations

This repository does **not** provide HTTPS termination, managed secret
rotation, email verification or reset delivery, rate limiting, account
deletion, retention automation, encrypted database backups, central audit
logging, intrusion detection, security monitoring, or role-based clinical
access. It must not be represented as enterprise-grade or production-ready.

## Before any deployment

Use HTTPS, a persistent high-entropy secret manager, managed MySQL access and
backups, rate limiting, CSRF review for the deployed topology, verified email
and reset flows, consent withdrawal/deletion, retention and incident-response
policies, independent security testing, and clinician/legal governance.

## Bounded public-hosting preparation

The local launcher remains loopback-only with one worker by default to avoid
duplicating optional models in memory. Do not infer HTTPS, shared throttling,
trusted-proxy handling, secure database transport, protected backups or incident
monitoring from local success or from a Dockerfile. Verify the actual hosting
topology and operational owners before public use. A persistent high-entropy
session secret must be shared across production workers; a random per-process
fallback is only a local-development convenience.

### Browser request boundary and compatibility limits

`DERMAMATRIX_TRUSTED_ORIGINS` is a comma-separated list of exact HTTP(S)
origins such as `https://app.example.test` (an illustrative domain, not a
configured deployment). Paths, credentials, null origins and malformed entries
are refused. Host case and default ports are normalized; another port,
scheme or host is a different origin even when both hosts are configured.
The request scheme and host come from the WSGI server. This app does not add
`ProxyFix`, trust arbitrary Forwarded/X-Forwarded headers, expose local LAN
addresses, or infer trusted proxy counts. An HTTPS proxy must supply the
correct WSGI scheme through a separately reviewed trusted server/proxy setup;
internal health checks must also use a configured request origin.

Command-line and legacy API clients with no Origin, Referer or Fetch Metadata
headers remain supported. Non-browser clients can forge those headers, and
older browsers or privacy tools can omit them. The checks are a bounded
same-origin browser mitigation, not authentication or a complete CSRF token
protocol. SameSite cookies, owner authorization and explicit consent guards
remain separate controls. Other safe GET endpoints keep their current
contracts; this change does not reclassify every GET as a write. Actual public
proxy topology, CSRF requirements, throttling, inference budgets and operational
protection still need verification before deployment.

See the [OWASP CSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
for Origin/Referer and Fetch Metadata tradeoffs. These source-level controls do
not establish the configuration of any public host.

[The upgrade decision register](audit-upgrade-decisions.md) records focused
acceptance checks for deployment, rights handling and eligibility. These notes
do not add retention automation, erasure, guardian verification, or a clinical
service, and no existing health records should be deleted to demonstrate them.
