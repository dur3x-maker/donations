# Automated MVP audit test plan

## Functional map

- Authentication: registration, login, access/refresh JWT, active-user checks, rate limits.
- User profile: contribution progress, dashboard, impact profile, public profile, anonymous contribution linking.
- Campaigns: catalog, details, creation unlock, one unfinished campaign rule, edit/delete ownership.
- Contributions and payments: registered/anonymous donations, immediate mock payment confirmation, campaign balance, realtime events.
- Subscriptions: automatic subscription after confirmed registered donation, one subscription per user/campaign.
- Notifications: donation, goal reached, update/photos, completion report, achievements, campaign unlock, patron circle.
- Updates: author-only publication for active campaigns, optional photos, subscriber notifications.
- Completion: goal transition to `AWAITING_REPORT`, photo-required report, `COMPLETED` transition, gratitude wall/supporters.
- Reputation and impact: author aggregate reputation, donor counts, levels, achievements, patron circle.
- Moderation: reports, suspicious flags, hide/restore permissions.
- Realtime: campaign, catalog and owner-dashboard WebSocket topics.

## Critical business flows

1. Registration/login -> authenticated access.
2. Successful payment -> exactly one confirmed contribution and exactly one balance increment.
3. Confirmed registered donation -> exactly one subscription and threshold evaluation.
4. Goal reached -> campaign closes for donations and subscribers are notified once.
5. Author update/report -> only owner can publish; subscribers receive the expected notifications.
6. Completion report -> photo required, status becomes completed, reputation and supporter-facing data change.
7. Achievement/level/patron thresholds -> deterministic boundary behavior without duplicates.

## Scenarios

### 1. Authentication

- Successful registration and normalized identity.
- Successful login.
- Wrong password.
- Unknown user.
- Duplicate email and username.
- Empty/invalid/oversized credentials.
- Access to protected endpoint without or with invalid token.

### 2. User Profile

- Empty profile.
- Contribution counters and totals.
- Anonymous contribution linking is repeat-safe.
- Owner dashboard isolation.
- Public profile does not expose private fields.

### 3. Campaigns

- Create after unlock.
- Reject create before unlock.
- Reject second unfinished campaign.
- View/list campaign.
- Owner edit/delete.
- Foreign-user edit/delete rejection.
- Validation of empty and oversized fields.

### 4. Contributions

- Registered, repeated and sequential donations.
- Anonymous donation and token reuse.
- Minimum amount and closed campaign rejection.
- Campaign amount and contributor counters.

### 5. Payments

- Successful confirmation.
- Repeated confirmation is idempotent.
- Failed payment transition.
- Concurrent/double confirmation risk.
- One payment per contribution.

### 6. Notifications

- Donation received.
- Goal reached.
- Update and photo notifications.
- Completion report.
- Achievement and patron notifications.
- Read access is owner-only.
- No duplicate threshold notifications.

### 7. Campaign Updates

- Owner publication with/without photos.
- Foreign-user rejection.
- Closed campaign rejection.
- List/detail behavior.

### 8. Completion Reports

- Owner publication after goal.
- Photo is mandatory.
- Wrong lifecycle status rejection.
- Repeated publication rejection.
- Subscriber notification.
- Campaign status and author reputation update.

### 9. Reputation

- Created/completed/reported/unfinished campaign counts.
- Raised amount.
- Public access and unknown user.

### 10. Achievements

- `FIRST_CONTRIBUTION`.
- `FIVE_CONTRIBUTIONS`.
- `PATRON_CIRCLE`.
- Achievement and notification uniqueness.

### 11. Levels

- Boundaries at 1, 5, 20, 50 and 100 contributions.
- Values immediately below and above thresholds.

### 12. Patron Circle

- 49/50/51 contribution boundaries.
- `patron_since`, achievement and notifications.
- Community patrons listing.

### 13. Permissions

- Foreign notification.
- Foreign campaign update creation.
- Foreign completion report creation.
- Foreign campaign mutation.
- Moderator-only endpoints.

### 14. Edge Cases

- Empty and very long strings.
- Double request / repeated form submission.
- Repeated payment confirmation.
- Repeated report publication.
- Repeated achievement evaluation.
- Duplicate-prone rows: subscriptions, achievements, activities, notifications, completion reports and payments.
