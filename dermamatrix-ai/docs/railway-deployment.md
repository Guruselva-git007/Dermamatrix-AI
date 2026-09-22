# Railway deployment

Railway is the selected public-hosting target for this project because it can
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
   FLASK_SECRET_KEY=<new long random secret>
   FLASK_SESSION_SECURE=true
   WEB_CONCURRENCY=1
   ```

   If the database service has a different name, replace `MySQL` in each
   reference with that service name. Do not copy a local `.env` file to
   Railway.
5. Deploy the web service and generate a public domain. Its health check is
   `/api/health`; a healthy deployment reports `mysql-connected`.
6. Put the generated public URL in the repository's GitHub homepage field and
   in the root README so teammates use the live application URL rather than a
   local address.

## Runtime boundary

The public app retains the project’s existing educational and research-only
model constraints. The dermatoscopic ResNet-34 route remains research-only,
uncalibrated, and attestation-gated; no disabled hair, nail, segmentation, or
rejected experimental model is enabled by this deployment.
