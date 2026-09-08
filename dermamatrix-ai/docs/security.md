# Local prototype security posture

DermaMatrix AI is a local final-year-project prototype, not a production
health-service security implementation. This document records what the
repository actually enforces and what remains required before deployment.

## Implemented controls

- Account passwords are persisted only as salted Werkzeug password hashes.
- Flask uses signed, HTTP-only, `SameSite=Lax` session cookies. The cookie is
  marked `Secure` only when `FLASK_SESSION_SECURE=true` behind HTTPS.
- Authenticated records are resolved from the server-side session; browser
  request bodies cannot select another user's profile, assessment, routine,
  report, or history export.
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
