"""Platform adapters for the Publish Spider. Each adapter is replaceable and
fail-closed: no credentials in the environment means a failed/skipped receipt,
never an exception and never a post."""
