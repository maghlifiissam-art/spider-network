# View counting security

Deployed 2026-10-07. Client revision: 1152485c485517bdeae2c82300cc90f46bef37eb.

## Contract

All `posts`, including sponsored `topic='ads'` posts, count at most once per rolling hour per verified account or signed visitor. Only `ads` table rows use one accepted view per Africa/Casablanca calendar day and the unchanged 500-view free cap. Sponsored posts are not sold or capped as paid ads by this implementation.

Signed-in accounts are verified through Supabase Auth, never a caller-supplied user ID. Anonymous visitors receive a server-signed token with 30-day expiry. Resetting storage or switching browsers can create a new visitor: this is best-effort browser deduplication, not proof of one person. There are no IP limits or trusted-IP claims. Forwarding-header provenance was not verified.

The endpoint checks exact origin, method, body size, fields, UUID, bearer validity and visitor signature/expiry. It uses purpose-separated HMAC actor identifiers, without storing raw bearer tokens or IPs. Request budgets: 120/actor/minute, 600 visitor issuances/minute, 6000 count requests/minute globally. Global budgets are pressure controls and can temporarily deny legitimate requests under attack; they do not guarantee distributed-bot prevention. Production traffic should guide changes before limits become disruptive.

Receipts and budgets have RLS enabled, zero client privileges and no client-facing policies. `record_view` and `view_token_budget` are executable only by service_role. Receipt/ad-row locks make updates atomic; missing, duplicate, capped or budget-rejected calls never increase view totals. Inactive receipt cleanup is bounded and retains current dedup windows. The browser has no fallback to the old RPCs. `bump_view` and `ad_view` client EXECUTE is revoked. Direct authenticated view-column UPDATE is blocked by new triggers; existing RLS/policies and unrelated triggers were preserved.

## Price is dormant

Private `ad_budget` stores integer 1000 microdollars per paid view ($0.001, or $1/1000). Its constraints currently require funded=spent=0 and state free/paused. No funded serving, payment collection, credit transition, invoice, refund or UI price announcement exists. `ad_funding_receipts` has a unique provider transaction ID, but no public funding path. Future verified funding/serving requires separate review and migration. Existing ads would default to free/zero; the ads table was empty at deployment.

## Verification

- Full migration and cutover editor models compared with local source before Run.
- Rollback-isolated SQL tests: 499->500, no 501, daily duplicate/new day, hourly duplicate/exact boundary, missing target leaves daily totals unchanged, client grant denial and budget rejection.
- Live PostgreSQL: 2026-10-07 22:59:59 UTC renders 23:59:59 Casablanca; 23:00 UTC renders 2026-10-08 00:00.
- Real confirmed canary through actual feed UI: two visible/preloaded posts each 0->1; reload/reopen left counts/receipts unchanged. No personal-account bearer was retrieved.
- Ten concurrent anonymous requests on one real post: exactly one accepted, nine duplicates. One test view remains honestly recorded.
- Forged visitor token and invalid bearer rejected; unknown fields/wrong origin rejected; no missing-target increment.
- Fresh catalog: all four new tables RLS true, client SELECT false; old/new counting RPC anon/auth EXECUTE false. Direct old anon RPCs fail 42501.
- Actual desktop feed and player visually inspected; no console error during canary test.

## Canary

User ID: `c187b8eb-628f-4315-8457-81696e7a15fe`. Dedicated security canary, not a customer's account. It consumes one early-account slot and appears in member counts. Credentials are not in this repository. No channel or ad was created. Exclude this ID from business metrics or remove it through an approved cleanup when no longer useful.

## Rollback and remaining limits

Disable counting temporarily if necessary, never restore insecure public RPC grants. Signing-secret rotation invalidates visitor tokens and resets best-effort anonymous identity. No historical totals were rewritten. Signed-user verification failure denies counting rather than silently treating that account as anonymous.
