# Anti-hallucination spider v1

## What this proves

This is a deterministic, dependency-free check, not an LLM vote. Structured claims must match facts from trusted source adapters with approved IDs, revision and SHA-256 pins and freshness limits. Exact decimal strings are compared without float arithmetic. Missing sources, unsupported types, stale/future evidence, changed content and conflicting evidence block. Facts and their pins must be supplied by an independently trusted adapter/operator, never the drafting model. A claim match does not release arbitrary prose.

Sources do not authorize anything. Instructions embedded in pages, tickets or facts are data, never permission. A receipt is a check result, not an authorization, signature or reusable send token. This is not a network-wide guard until each consumer calls it at its final output boundary. It does not inspect generated images, engineering artifacts or every existing publication workflow.

## RIMAZ support first lane

Only `report_problem`, complete and verbatim, in en/fr/ar/ary is eligible. Category must be content, bug or other. Password/account security, money, legal, reputation and ambiguous requests still escalate. Store-opening FAQ currently contains membership/free-period terms, so it is intentionally excluded. Spanish/Portuguese/German/Turkish templates are not silently translated or given English fallback.

The customer-service operator must independently confirm that the ticket is a plain reporting/how-to request. The category label alone cannot establish eligibility: an other/bug ticket can still contain security or money content. Never classify solely by keywords. If in doubt leave open and escalate.

Immediately before posting:

1. Re-read the live open ticket and establish the routine scope and sending authority.
2. Read current repo verifier and approved registry. Use a clean current checkout.
3. Write the exact selected template to a private UTF-8 draft file without an added newline.
4. Run:

   `python3 scripts/verify_rimaz_support.py --draft-file /tmp/reply.txt --ticket-id <real-id> --language ar --category content --faq-id report_problem`

5. Only exit 0, `template_match` and `release_allowed:true` can proceed. Match the ticket ID and SHA-256 of the final bytes to the receipt. Check the current time is before expires_at. Any edit, redirect, missing source, expired receipt, FAQ hash change or failed command blocks. Rerun when needed.
6. Confirm ticket still open and final bytes unchanged. Respect the database guards. Existing permissions, review requirements and escalation still apply. Never modify a trigger/policy to get a reply through.
7. Store only the JSON receipt in a private operational log, not the public repo. Do not log draft, ticket body, identity, credentials or source payload. Do not persist this test's fixture ID as a real customer receipt.

The command performs one fresh HTTPS fetch of the fixed deployed support page and permits no redirect. It never sends, changes tickets, handles credentials or invokes an LLM. The gate blocks when the live page differs from the reviewed pinned snapshot. A reviewed FAQ update needs an independently reviewed registry refresh; it must not auto-learn new facts from arbitrary live content. The revision identifies the reviewed source commit, while hash equality proves live correspondence. Source text is not executed.

The 60-second window starts at source observation, not the later check. The caller must enforce expiration at the final posting boundary. This initial operator integration is procedural, not an unbypassable database constraint. A future server-side consumer must enforce the same check in its send transaction.

## Other consumers

Use verify_claims only with adapter-produced facts and operator-controlled pins. Bind all final visible text to reviewed templates or an independently reviewed complete claim-to-text mapping. Do not accept a drafting model's claim inventory as proof that every sentence is covered. `claims_match` always has `release_allowed:false` to prevent this mistake. Unsupported prose goes back for correction or human review. Do not change publication behavior without consumer-specific integration review.

`qa_spider` remains an advisory consistency/style filter. `agent_chain` no longer marks its LLM verdict as ready to publish: it always returns a draft requiring factual verification, with release disabled. No publishing side effect is added.

## Tests

`python3 -m unittest discover -s tests -p test_anti_hallucination_spider.py -v`

Includes invented facts, wrong prices, float/coercion rejection, missing allowlist, conflicts, stale/future evidence, revision/hash changes, unsourced additions, omitted template text, forbidden topics, missing translations, and private-content-free receipts. Live preflight must be tested separately; it is not a customer submission/reply test.
