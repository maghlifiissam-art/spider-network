# Public read contract

These five postgres-owned views deliberately provide public aggregates and badges without granting access to their private source tables. Keep their definer behavior and existing anonymous read values. Their Security Advisor definer-view notices are known exceptions, not permission to ignore new drift.

| View | Exact public columns |
| --- | --- |
| channel_stats | id, handle, name, bio, avatar_url, owner_id, followers, reels |
| founder_badges | user_id, founder_no |
| early_badges | user_id, early_no |
| post_counts | post_id, comments, reactions, likes, follow_only, comments_off, views, followers |
| channel_stars | channel_id, views, followers, stars |

UUIDs in this contract are public identifiers. Emails, roles, membership details, messages, payments, earnings and owner settings are not part of it.

All definitions select explicit fields, never SELECT *. Preserve founder badge store-seat precedence, existing count definitions and star thresholds. Definitions use built-in aggregates and no application SECURITY DEFINER function. Client EXECUTE grants are therefore not required by these views.

anon and authenticated must have SELECT only on these views. PUBLIC must confer no write privilege. Check effective privileges, including column-level grants and role inheritance. Never grant INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES or TRIGGER to clients. Keep private-table RLS/grants unchanged.

## Audit baseline

Compare exact column order, types, view definitions, ownership, grants and referenced functions against the approved contract. Flag new columns, new definer objects, changed definitions, new privileges or unexpected source/function dependencies. Do not repeatedly report the same five accepted definer-view notices while this contract remains unchanged. Other advisor findings are not covered by this exception.

## Hardening recorded October 7, 2026

Removed non-SELECT client privileges from the five public views. No public read values or business rules changed.

Fixed search_path=pg_catalog on items_limit(), stores_seat_guard(), protect_early(), protect_founder() and protect_role(). Application references in those bodies are schema-qualified; bodies, trigger bindings and limits are unchanged.

View-count RPC rate limiting and deduplication remain pending an explicit repeat-watch counting rule. The 500 free ad-view allowance, prices and star thresholds must not change without the owner's decision.
