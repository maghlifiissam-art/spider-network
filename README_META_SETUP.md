# Meta setup: explicit destinations, dry-run first

This change does not publish content or enable unattended posting. It removes the
implicit first-Page selection. Keep `config/publish.yaml` at `dry_run: true`.

## Credentials

Use your own Meta app, and grant only the Pages needed. For Page content setup the
scopes are `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, plus
the default profile scope. Instagram needs its own setup and permissions; this
Pages setup does not authorize it. Endpoint-specific video eligibility and public
visibility must be verified separately before approving a real publication.

Official token documentation (read 2026-10-26, updated 2026-06-30):
https://developers.facebook.com/documentation/facebook-login/guides/access-tokens/get-long-lived

A valid short-lived User token, own App ID and App Secret can be exchanged
server-side for a long-lived User token, generally about 60 days. An expired
short-lived token cannot be exchanged. Derived long-lived Page tokens have no
scheduled expiration but can still be invalidated; do not promise permanent access.

`python scripts/auth_meta.py --help` describes the setup interface. Supply secret
file paths, never secret literals in shell history. Provide every intended Page
ID explicitly using repeated `--page-id`, and an output directory outside the
checkout. The helper checks app ID, exact granular Page grants, content tasks and
derived Page token identity. It writes mode-0600 files in a mode-0700 directory.
It does not upload credentials to a hosting service or save them in git. Move
validated credentials to the chosen private secret store, then remove temporary
files. Do not run this helper as a publication test.

## Destination contract

Every Facebook job must carry `facebook_page_id`. No title, brand string, Page
list order, legacy `META_PAGE_ID`, or default Page is used as fallback.

The non-secret `META_PAGE_TOKEN_ENV_MAP` maps an allowed Page ID to the NAME of a
secret environment variable, not to a token value. Example with fictitious IDs:

```json
{"111": "META_BRAND_A_PAGE_TOKEN", "222": "META_BRAND_B_PAGE_TOKEN"}
```

Populate each referenced variable through the deployment's secret store with its
verified matching Page token. Missing/unknown Page IDs, malformed mappings and
missing credentials fail closed without sending a request. Keep the mapping and
credentials separate. Never put a token, App Secret or private metadata in this
public repository.

## Remaining release gates

- Confirm the chosen deployment environment and secure credential storage.
- Check actual token metadata, validity and revocation handling; arrange bounded
  read-only health checks, not automatic content tests.
- Verify the exact intended video endpoint, permissions, app eligibility and
  visibility. This patch does not assert these are satisfied.
- Obtain approval for the particular content and its exact Page destination.
- Only then deliberately change dry-run for that approved job. A successful
  credential check is never permission to publish.

Tests use mocks and fictitious identifiers, never real tokens or uploads:
`python -m unittest tests.test_meta_publisher tests.test_publish_spider -v`.

## Video upload route (not live-tested)

The Facebook adapter follows Meta's uploaded-file-handle flow: own App ID and
long-lived USER token create an upload session, upload MP4 bytes with OAuth header,
then the explicit Page token publishes the returned handle via graph-video.
Set META_APP_ID and META_USER_ACCESS_TOKEN in the verified runtime's secret store,
in addition to the per-Page mapping. No write is retried automatically. A timeout
is unconfirmed and must be reconciled before a deliberate retry. A returned video
ID does not establish public visibility. Dry-run never uploads bytes or creates
an upload session. This implementation still requires endpoint eligibility and
an approved item before live testing.

Official sequence: https://developers.facebook.com/documentation/video-api/guides/publishing
