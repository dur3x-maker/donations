# MVP automated audit report

## Result

- Automated pytest cases: **70**
- Passed: **70**
- Failed: **0**
- Backend compile check: passed
- Alembic head: `0014_unfinished_campaign_invariant`
- Frontend lint: passed with 7 `no-img-element` performance warnings
- Frontend production build: passed with required API environment variables

## Fixed defects

1. Payment confirmation locked only the payment, not the campaign. Concurrent payments could lose a campaign balance increment or duplicate goal-transition effects. Campaign rows are now locked during confirmation.
2. Subscription and achievement creation used race-prone `SELECT -> INSERT`. User-scoped locking now serializes threshold and subscription mutations.
3. Concurrent campaign creation could bypass the “one unfinished campaign” rule. Added owner locking, conflict handling and a PostgreSQL partial unique index.
4. Concurrent completion-report publication could pass both prechecks. The campaign row is now locked before lifecycle validation.
5. Campaign `contributors_count` counted contributions instead of unique participants. It now groups registered users and anonymous tokens correctly.
6. Completion-report supporter wall collapsed all anonymous donors into one supporter. Distinct anonymous tokens are now distinct supporters.
7. An owner could lower a campaign target to/below the already collected amount, leaving lifecycle status and notifications inconsistent. Such edits now return `409`.
8. Whitespace-only campaign/update/report text passed validation. Required text is now trimmed before length validation.
9. Update/report photo URLs longer than the database column limit could reach the DB and fail as `500`. Item-level length validation now returns `422`.
10. Concurrent duplicate registration could surface as an unhandled integrity error. It now returns `409`.
11. Profile summary could fail with `500` when stored timestamps were timezone-naive. Datetimes are normalized before threshold comparison.
12. Pydantic field warning for the public JSON key `copy` was removed without changing the API response contract.

## Coverage

- Authentication and token-protected access.
- User/profile impact and public-profile privacy.
- Campaign create/view/edit and ownership.
- Registered, anonymous and repeated contributions.
- Payment success/failure/idempotency.
- Automatic subscriptions and duplicate prevention.
- Goal, update, photo, report, achievement and patron notifications.
- Completion reports, required photos and lifecycle transitions.
- Author reputation.
- Achievement thresholds and duplicate prevention.
- Level boundaries: 1, 5, 20, 50, 100.
- Patron boundaries: 49, 50, 51.
- Permissions and moderator restrictions.
- Empty/oversized values, repeated forms and database uniqueness constraints.

## Manual / environment-dependent checks

1. Run Alembic `upgrade head` against a copy of the real PostgreSQL database.
2. Before migration `0014`, check whether existing data already contains multiple active unfinished campaigns per owner; the unique index will correctly reject inconsistent data.
3. Run concurrent PostgreSQL tests for:
   - two payment confirmations for one campaign;
   - two first donations by one user to one campaign;
   - two campaign-create requests by one owner;
   - two completion-report publications;
   - simultaneous achievement evaluation at thresholds.
4. Run WebSocket delivery/reconnect tests with a live ASGI server.
5. Test upload storage, MIME spoofing, file size and cleanup on the deployed filesystem/object storage.
6. Test real payment provider callbacks when the mock immediate-success provider is replaced or enabled.
7. Browser E2E and accessibility checks remain outside this pytest backend suite.

## Remaining risks

- PostgreSQL and transaction-lock behavior was reviewed and hardened but not executed locally because Docker Desktop was unavailable.
- Notification rows do not have a generic event idempotency key. Current critical threshold paths are serialized, but future background retries should use explicit event keys/outbox semantics.
- WebSocket messages are in-memory and are not durable across process restarts or multiple backend replicas.
- Uploads are stored on local disk; horizontal scaling requires shared/object storage.
- Frontend has seven unoptimized `<img>` warnings affecting performance, not functional correctness.
