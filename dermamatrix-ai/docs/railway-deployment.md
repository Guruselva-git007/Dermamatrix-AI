# Railway deployment

These are configuration notes for a possible deployment, not evidence of a
hardened live host or authorization to publish. Public/patient-facing use still
requires the decisions and controls in [security](security.md) and
[the upgrade decision register](audit-upgrade-decisions.md). Do not upload the
local database, health records, private images or `.env` files.

Railway is the recorded public-hosting target for this project because it can
build the Flask service from GitHub and provide a managed MySQL service in the
same private network. The tracked Dockerfile includes the exact, checksum-
verified research ResNet-34 artifact used by the local app; raw datasets,
previous workspaces, reports, local databases, and secrets never leave the
canonical workspace or enter Git.

## One-time Railway setup

1. Create a Railway project and add a **MySQL** service.
2. Add a GitHub service from `Guruselva-git007/Dermamatrix-AI` on `main`.
3. In the web service **Settings**, set **Root Directory** to
   `/dermamatrix-ai`. Railway automatically uses the Dockerfile found there.
   Set its health-check path to `/api/health`, timeout to `180` seconds, and
   restart policy to **On Failure** with `10` retries.
4. In the web service **Variables**, reference the MySQL service values:

   ```text
   MYSQL_HOST=${{MySQL.MYSQLHOST}}
   MYSQL_PORT=${{MySQL.MYSQLPORT}}
   MYSQL_USER=${{MySQL.MYSQLUSER}}
   MYSQL_PASSWORD=${{MySQL.MYSQLPASSWORD}}
   MYSQL_DATABASE=${{MySQL.MYSQLDATABASE}}
   DERMAMATRIX_ENV=production
   DERMAMATRIX_TRUSTED_ORIGINS=<exact verified HTTPS application origin>
   FLASK_SECRET_KEY=<new long random secret>
   FLASK_SESSION_SECURE=true
   WEB_CONCURRENCY=1
   ```

   If the database service has a different name, replace `MySQL` in each
   reference with that service name. Do not copy a local `.env` file to
   Railway. The trusted origins setting must identify the actual application
   origin, for example `https://app.example.test` (illustrative only), with no
   path or trailing slash; separate multiple approved origins with commas.
   The app does not guess a public hostname. Configure the public domain before
   activating explicit production mode, and arrange health checks to use a
   configured request origin. Production mode checks bounded prerequisites;
   generate a persistent high-entropy secret of at least 32 characters and
   verify actual HTTPS termination separately. The WSGI server must receive
   the correct external request scheme and host through a separately reviewed
   trusted proxy/server setup; arbitrary Forwarded/X-Forwarded headers are not
   trusted by an added `ProxyFix` layer. The browser-origin/Fetch Metadata guard
   is a bounded same-origin mitigation, not a complete CSRF token protocol or
   evidence of shared throttling, backup recovery or incident monitoring.
5. Deploy the web service and generate a public domain. Its health check is
   `/api/health`; a healthy deployment reports `mysql-connected`.
6. Put the generated public URL in the repository's GitHub homepage field and
   in the root README so teammates use the live application URL rather than a
   local address.

## Runtime boundary

Any deployment must retain the project’s existing educational and research-only
model constraints. The Dockerfile explicitly installs only the checksum-pinned
dermatoscopic ResNet-34 artifact. Its route remains research-only,
uncalibrated and attestation-gated. The local workspace also has separate
ordinary-Skin and ten-class Nail research adapters, but their ignored local
weights are not automatically included in that image; configured support is
not runtime availability. Check `/api/model-registry`, actual host artifacts,
dependencies and request-specific failures separately. Hair condition
classification and rejected SCIN/three-class nail experiments remain
unavailable. See [the current capability contract](capability-contract.md).

Before building or distributing an image, review the model/data permissions
and notices in the [permission register](audit-upgrade-decisions.md#dm-09--permission-register).
A checksum verifies artifact identity, not permission or clinical readiness.
