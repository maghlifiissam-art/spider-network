"""Deterministic evidence checks. No network, LLM, authorization or sending here."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re


def digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError('timezone required')
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class Source:
    id: str
    revision: str
    content: str
    observed_at: datetime
    facts: dict[str, tuple[str, str]]  # key -> (type, value), supplied by trusted adapter


@dataclass(frozen=True)
class Pin:
    revision: str
    sha256: str
    max_age_seconds: int


@dataclass(frozen=True)
class Claim:
    source_id: str
    key: str
    kind: str
    value: str


def canonical(kind: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError('values must be strings, never binary floats')
    if kind == 'text':
        return value
    if kind == 'integer' and re.fullmatch(r'-?(0|[1-9][0-9]*)', value):
        return str(int(value))
    if kind == 'decimal' and re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?', value):
        return str(Decimal(value).normalize())
    raise ValueError('invalid type or exact value')


def source_errors(source: Source, pin: Pin, now: datetime) -> list[str]:
    errors = []
    if source.revision != pin.revision or digest(source.content) != pin.sha256:
        errors.append('source_revision_or_hash_mismatch')
    age = (utc(now) - utc(source.observed_at)).total_seconds()
    if pin.max_age_seconds <= 0 or age < 0 or age > pin.max_age_seconds:
        errors.append('source_stale_or_future')
    return errors


def verify_claims(claims: list[Claim], sources: dict[str, Source],
                  pins: dict[str, Pin], now: datetime) -> dict:
    """Claim correspondence only. Does NOT certify any surrounding free-form prose."""
    issues = []
    if not claims:
        issues.append('no_claims')
    for index, claim in enumerate(claims):
        prefix = f'claim_{index}:'
        source, pin = sources.get(claim.source_id), pins.get(claim.source_id)
        if source is None or pin is None:
            issues.append(prefix + 'unallowlisted_or_missing_source')
            continue
        try:
            issues.extend(prefix + e for e in source_errors(source, pin, now))
            fact = source.facts.get(claim.key)
            if fact is None:
                issues.append(prefix + 'missing_fact')
            elif claim.kind != fact[0] or canonical(claim.kind, claim.value) != canonical(*fact):
                issues.append(prefix + 'fact_mismatch')
            # Multiple approved evidence records cannot silently disagree on a fact.
            for other_id, other in sources.items():
                other_pin = pins.get(other_id)
                if other_pin and claim.key in other.facts:
                    issues.extend(prefix + e for e in source_errors(other, other_pin, now))
                    if other.facts[claim.key][0] != claim.kind or canonical(*other.facts[claim.key]) != canonical(claim.kind, claim.value):
                        issues.append(prefix + 'conflicting_evidence')
        except (ValueError, TypeError, InvalidOperation, OverflowError):
            issues.append(prefix + 'invalid_evidence')
    return {'decision': 'blocked' if issues else 'claims_match',
            'scope': 'structured_claims_only', 'release_allowed': False,
            'issues': sorted(set(issues))}


def verify_support(draft: str, ticket_id: str, language: str, faq_id: str,
                   category: str, source: Source, registry: dict,
                   now: datetime) -> dict:
    """Exact, complete template only. Eligibility/authority remain caller duties."""
    issues = []
    try:
        pin = Pin(registry['revision'], registry['sha256'], 60)
        if source.id != registry['source_url']:
            issues.append('unallowlisted_source')
        issues.extend(source_errors(source, pin, now))
        if faq_id != 'report_problem' or category not in ('content', 'bug', 'other'):
            issues.append('escalate_topic')
        expected = registry['templates'].get(language, {}).get(faq_id)
        if not expected:
            issues.append('unsupported_language_or_template')
        elif draft != expected:
            issues.append('draft_not_exact_complete_template')
        if not ticket_id or len(ticket_id) > 128:
            issues.append('invalid_ticket_id')
        expires = (utc(source.observed_at) + timedelta(seconds=60)).isoformat()
    except (KeyError, ValueError, TypeError, OverflowError):
        issues.append('invalid_registry_or_evidence')
        expires = None
    return {'schema': 'verification.v1', 'decision': 'blocked' if issues else 'template_match',
            'release_allowed': not issues, 'ticket_id': ticket_id,
            'draft_sha256': digest(draft), 'source_url': source.id,
            'source_revision': source.revision, 'source_sha256': digest(source.content),
            'checked_at': utc(now).isoformat(), 'expires_at': expires,
            'issues': sorted(set(issues)), 'scope': 'exact_support_template',
            'authorization_granted': False}


def receipt_json(result: dict) -> str:
    """Receipt deliberately excludes draft, source content, ticket body and user ID."""
    return json.dumps(result, ensure_ascii=False, sort_keys=True)
