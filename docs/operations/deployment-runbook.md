# Deployment Runbook (Basic)

This is a lightweight runbook for backend deployment and immediate verification.

## Preconditions

- Deployment target is healthy (service/container platform operational)
- Required secrets/environment variables are present — see `environment-variables.md`
- Database is reachable
- Redis/broker is reachable (if using Celery/Channels)

## Deployment steps

1. **Choose release commit**
   - Staging deploys from `staging`, populated via a periodic PR (base `staging`, head `development`)
   - Production deploys from `main`, populated via a periodic PR (base `main`, head `staging`)
   - `main` is the repo's default branch
2. **Build and deploy application image/artifact**
   - Platform: Render, region `frankfurt` for all services
   - Staging: services `web-staging` / `celery-staging` / `celery-beat-staging`, config `render-staging.yaml`, env group **"Staging env"**
   - Production: services `web` / `celery` / `celery-beat`, config `render.yaml`, env group **"Prod env"**
3. **Run migrations**
   - This repo includes `scripts/pre-deploy.sh` which runs:

   ```bash
   python manage.py migrate
   ```
4. **Restart application services**
   - Web/API process
   - Worker/scheduler processes (`celery`, `celery-beat` for the relevant environment)

## Post-deploy verification checklist

- Health endpoint or basic request returns success
- Django admin/API login/auth flow works
- A representative API endpoint returns expected response
- Background jobs enqueue and execute
- Error monitoring shows no immediate regression spike
- Transactional email sends successfully — see `send_test_email` command in `environment-variables.md`; note the web *and* Celery worker both need matching email config, since confirmation emails are queued through Celery

## Rollback guidance (basic)

- Roll back to previously known-good deployment artifact
- Re-run service restart to ensure all processes are on rollback version
- If a migration is backward-incompatible, follow project-specific DB rollback procedure before re-deploying old code

## Operational notes

- Keep migrations small and reversible where feasible
- Prefer additive schema changes prior to destructive cleanups
- Announce deploy windows for higher-risk changes

### Removing a database column safely

`web`, `celery`, and `celery-beat` (and their `-staging` equivalents) are
separate Render services, each with its own `autoDeployTrigger: commit` and
build queue. Only `web` has a `preDeployCommand` that runs `migrate`; `celery`
and `celery-beat` have none. All three deploy independently off the same
commit, with no guarantee they finish building/restarting at the same time —
`celery`/`celery-beat` builds can lag `web` by anywhere from seconds to a
couple of hours depending on Render's build queue.

Because of this, a migration that drops a column in the same deploy as the
code change that stops using it creates a window where `web` has already
migrated the (shared) database but `celery`/`celery-beat` are still running
the *old* image — which still references the now-dropped column — until
their own deploys catch up. Any query touching that model from the old
worker code raises `UndefinedColumn` for the whole window. (This is what
happened with `Character.can_link` on 2026-08-14: the migration removing the
column landed in the same deploy as the code that stopped needing it, and
`commute_tick`/`wander_tick` errored on the stale `celery`/`celery-beat`
workers until they finished redeploying.)

To remove a column without a stale-worker error window, split it across two
separate deploys (expand/contract):

1. **Deploy 1**: ship the code change that stops reading/writing the column,
   but leave the column itself in the DB (no migration removing it yet).
2. Confirm `web`, `celery`, and `celery-beat` (and `-staging` equivalents)
   have all finished redeploying and are healthy.
3. **Deploy 2**: add the migration that drops the column, with no
   accompanying code change needed (the code already stopped touching it in
   deploy 1).

## Note on PR workflow

The rule for which branch a *feature* PR should target (normally `development`, with a documented exception for basing on `staging`) is a development workflow concern, not a deployment-execution step — that lives in `CLAUDE.md`, not here.
