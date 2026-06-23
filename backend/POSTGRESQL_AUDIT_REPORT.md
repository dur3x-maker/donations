# PostgreSQL concurrency audit

## Result

- PostgreSQL: **16-alpine**
- Tests executed against PostgreSQL: **76**
- Passed: **76**
- Existing tests: **70/70**
- New PostgreSQL concurrency/constraint tests: **6/6**
- Alembic head: `0015_campaign_owner_fk`
- `alembic check`: no schema drift
- Backend image build: passed
- Frontend image build: passed
- Full Docker Compose startup: all services healthy

## Verified concurrency scenarios

- Ten parallel confirmations of one payment:
  - one confirmation applied;
  - one campaign amount increment;
  - one subscription;
  - one `FIRST_CONTRIBUTION`;
  - one achievement notification;
  - one donation activity.
- Ten parallel `FIRST_CONTRIBUTION` evaluations:
  - one achievement;
  - one notification;
  - no transaction errors.
- Ten parallel patron evaluations at contribution 50:
  - one `patron_since`;
  - one `PATRON_CIRCLE`;
  - one patron notification.
- Two parallel completion-report publications:
  - one report;
  - one photo set;
  - campaign status `COMPLETED`;
  - competing request rejected with `409`.
- Two parallel campaign creations:
  - one unfinished campaign;
  - competing request rejected with `409`.
- Direct insert bypassing services:
  - PostgreSQL partial unique index rejects a second unfinished campaign.

## New defects found and fixed

1. Migration revision `0014_unfinished_campaign_invariant` exceeded Alembic's default `VARCHAR(32)` version column. A clean deployment failed before backend startup. Revision was shortened to `0014_unfinished_campaign`.
2. `campaigns.owner_id` was `NOT NULL`, while its PostgreSQL foreign key still used `ON DELETE SET NULL`; ORM expected `CASCADE`. Added migration `0015_campaign_owner_fk` with `ON DELETE CASCADE`.
3. ORM metadata drifted from existing migrations for completion-report uniqueness and the notification composite index. Metadata was aligned and `alembic check` is now clean.

## Not reproduced

- Duplicate payment application.
- Lost campaign amount update.
- Duplicate subscription.
- Duplicate achievement or patron notification.
- Duplicate completion report/photos.
- Parallel bypass of the unfinished-campaign rule.
- PostgreSQL deadlocks or serialization failures in the tested flows.
- Enum, index or unique-constraint conflicts during clean migration.

## Remaining risks before manual testing

- Tests cover targeted concurrency, not long-running soak/load behavior.
- The in-memory WebSocket broadcaster is not durable and was outside this PostgreSQL audit.
- External payment-provider callbacks are not present; only the current mock confirmation flow was tested.
- Generic notifications still have no event-idempotency key for future background retries.
- Frontend build retains seven `<img>` performance warnings; no functional build errors.
