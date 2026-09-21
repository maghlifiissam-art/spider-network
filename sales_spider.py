"""Deterministic Sales Spider orchestrator. Drafts only; never messages customers.

Sales Spider qualifies leads, prepares persuasion replies for human review,
closes only payment-verified deals, and records attribution and commissions.
Automatic sending, publishing and spending are disabled by design.
"""
from __future__ import annotations
import json
from pathlib import Path
from sales_contracts import (AttributionEvent, CommissionRecord, DealOutcome, Lead,
                             ObjectionScript, Product, ReplyDraft)

STAGES = ("lead_intake", "qualify", "reply_draft", "close_check", "confirm_order",
          "attribution", "commission_log", "handoff")


class OfflineAdapter:
    name = "offline_fixture"
    zero_cost = True

    def __init__(self, fixture_dir: str | Path = "fixtures"):
        self.fixture_dir = Path(fixture_dir)

    def load(self, name: str) -> dict:
        return json.loads((self.fixture_dir / name).read_text())


def qualify(lead: Lead, catalog: dict) -> bool:
    return lead.product_sku in catalog and catalog[lead.product_sku].active


def pick_objection(note: str, scripts: list) -> ObjectionScript | None:
    low = (note or "").lower()
    for script in scripts:
        if any(k.lower() in low for k in script.trigger_keywords):
            return script
    return None


def draft_reply(lead: Lead, product: Product, objection: ObjectionScript | None,
                draft_id: str) -> ReplyDraft:
    if objection is not None:
        body = objection.reply_template.format(product_name=product.name,
                                               price_mad=product.price_mad)
        oid = objection.objection_id
    else:
        name = (lead.name + " ") if lead.name else ""
        body = (f"مرحباً {name}! المنتج «{product.name}» متوفر بـ{product.price_mad} درهم. "
                "واش بغيتي نأكد الطلب؟")
        oid = None
    return ReplyDraft(draft_id=draft_id, lead_id=lead.lead_id, body=body, objection_id=oid)


def _campaign_of(source_ref: str) -> str:
    for part in source_ref.split("&"):
        if part.startswith("utm_campaign="):
            return part.split("=", 1)[1]
    return source_ref


class SalesSpider:
    route = "sales"

    def __init__(self, adapter=None, state_dir: str | Path = "state/sales"):
        self.adapter = adapter or OfflineAdapter()
        self.state_dir = Path(state_dir)

    def run_pilot(self, fixture: str = "sales_pilot.json") -> dict:
        spec = self.adapter.load(fixture)

        catalog: dict[str, Product] = {}
        for p in spec["catalog"]:
            product = Product(**p)
            product.validate()
            catalog[product.sku] = product

        scripts: list[ObjectionScript] = []
        for s in spec.get("objection_scripts", []):
            script = ObjectionScript(objection_id=s["objection_id"],
                                     trigger_keywords=tuple(s["trigger_keywords"]),
                                     reply_template=s["reply_template"])
            script.validate()
            scripts.append(script)

        valid_leads, rejected = [], []
        for raw in spec["leads"]:
            try:
                lead = Lead(**raw)
                lead.validate()
                valid_leads.append(lead)
            except (TypeError, ValueError) as exc:
                rejected.append({"lead": raw.get("lead_id", "?"), "reason": str(exc)})

        drafts, qualified_ids = [], []
        for i, lead in enumerate(valid_leads, 1):
            if not qualify(lead, catalog):
                rejected.append({"lead": lead.lead_id, "reason": "inactive or unknown product"})
                continue
            qualified_ids.append(lead.lead_id)
            product = catalog[lead.product_sku]
            objection = pick_objection(lead.note, scripts)
            drafts.append(draft_reply(lead, product, objection, f"draft-{i:03d}").review_dict())

        outcomes = []
        for raw in spec.get("outcomes", []):
            outcome = DealOutcome(**raw)
            outcome.validate()
            outcomes.append({"lead_id": outcome.lead_id, "product_sku": outcome.product_sku,
                             "status": outcome.status, "price_mad": outcome.price_mad,
                             "payment_verified": outcome.payment_verified})

        attribution = []
        for lead in valid_leads:
            event = AttributionEvent(lead_id=lead.lead_id, source_ref=lead.source_ref,
                                     campaign=_campaign_of(lead.source_ref),
                                     medium=lead.channel)
            event.validate()
            attribution.append({"lead_id": event.lead_id, "source_ref": event.source_ref,
                                "campaign": event.campaign, "medium": event.medium})

        commissions = []
        for i, raw in enumerate(spec.get("outcomes", []), 1):
            if raw.get("status") != "won":
                continue
            product = catalog[raw["product_sku"]]
            record = CommissionRecord(record_id=f"comm-{i:03d}", lead_id=raw["lead_id"],
                                      product_sku=product.sku, gross_mad=product.price_mad,
                                      commission_mad=round(product.price_mad * product.commission_rate, 2),
                                      beneficiary="owner")
            record.validate()
            commissions.append({"record_id": record.record_id, "lead_id": record.lead_id,
                                "product_sku": record.product_sku, "gross_mad": record.gross_mad,
                                "commission_mad": record.commission_mad,
                                "beneficiary": record.beneficiary, "status": record.status})

        result = {"contract_version": "sales.v1", "route": self.route,
                  "adapter": self.adapter.name, "zero_cost": bool(self.adapter.zero_cost),
                  "stages": list(STAGES), "pilot": spec["pilot"],
                  "qualified_leads": qualified_ids, "rejected_leads": rejected,
                  "reply_drafts": drafts, "outcomes": outcomes,
                  "attribution": attribution, "commissions": commissions,
                  "handoff_targets": ["secure_delivery_flow"],
                  "qa_decision": "go_draft" if drafts else "no_go",
                  "send_allowed": False, "publish_allowed": False}
        self.state_dir.mkdir(parents=True, exist_ok=True)
        (self.state_dir / f"{spec['pilot']['id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2))
        return result


def run_sales_spider(command: dict, adapter=None) -> dict:
    return SalesSpider(adapter=adapter).run_pilot(command.get("fixture", "sales_pilot.json"))


def route_sales(command: dict, adapter=None) -> dict:
    if command.get("domain") != "sales":
        return {"accepted": False, "reason": "wrong_route"}
    return run_sales_spider(command, adapter=adapter)
