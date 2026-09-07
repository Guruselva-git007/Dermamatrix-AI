# Account authentication and persistence

## Scope

DermaMatrix AI uses local MySQL records for registered accounts. This is a
college-project deployment, not a hosted identity service. The browser never
stores a password, password hash, patient identifier, or health history in
local storage.

## Account flow

1. `POST /api/auth/register` validates a name, email, password confirmation,
   and account-consent acknowledgement. A phone number is optional.
2. The server stores a salted `werkzeug.security.generate_password_hash` hash
   in `auth_accounts`; plaintext passwords are never persisted or returned.
3. The server creates a signed, HTTP-only, SameSite=Lax Flask session cookie.
   Its bounded lifetime is configured by `FLASK_SESSION_DAYS` (1–30; default
   14). Set `FLASK_SESSION_SECURE=true` only behind HTTPS.
4. On a page reload, the client calls `GET /api/auth/me`. The API resolves the
   user from the session server-side and returns the current user/profile plus
   durable non-clinical preferences.
5. `POST /api/auth/logout` clears only the browser session. It does not delete
   the account or its records.

No password-reset API is exposed because a real reset needs a verified email
delivery service and token lifecycle. The UI must not imply that an email was
sent when none was sent.

## Authorization model

`current_user()` is the source of ownership for authenticated routes. Routines,
check-ins, assessment metadata, review requests, reports, and history exports
are queried or written with that resolved `user_id`. The normal client flow no
longer sends a `patient_id`; an older `GET /api/profiles/<patient_id>` remains
only as a strict compatibility endpoint and can resolve the active user's own
identifier only. This prevents an authenticated account from selecting another
account's records through URL or request-body tampering.

Guest users can run an ephemeral assessment. Guest data, uploaded image bytes,
and reports are not stored.

## Additive MySQL migration

At application startup, `schema_migrations` records
`20260907_auth_profile_preferences_v1`. The migration is additive and preserves
existing data:

- adds `users.updated_at`, `users.last_login_at`, and `users.is_active` if absent;
- creates one `user_preferences` row per user with theme, notification, and
  reduced-motion choices;
- backfills missing preference rows and timestamps.

No passwords, users, assessments, routines, reports, or health history are
deleted or rewritten by the migration.

## API contracts

- `GET /api/auth/me` → `{ authenticated, user, profile, preferences }`; returns
  HTTP 401 after logout or an invalid/expired session.
- `GET /api/profile`, `PATCH /api/profile` → only the signed-in user's profile.
  Health-history writes require explicit `health_data_consent`.
- `GET /api/preferences`, `PUT /api/preferences` → only `theme`,
  `notifications_enabled`, and `reduced_motion`.
- `GET /api/routines`, `GET /api/progress-checkins`,
  `GET /api/analysis-history`, report downloads, and write routes derive the
  owner from the cookie. They return HTTP 401 when signed out and HTTP 404 for
  another account's record.

## Limitations and deployment requirements

This local prototype has no email verification, password-reset delivery,
rate-limiting layer, HTTPS termination, or multi-device session management.
For deployment, use a persistent high-entropy `FLASK_SECRET_KEY`, HTTPS,
secure cookie configuration, rate limiting, audited reset/verification flows,
and managed database backups/access controls. Do not use the local demo
configuration as production medical identity infrastructure.
