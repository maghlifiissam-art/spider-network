"""
monitor_spider.py
------------------
Script de surveillance automatique pour "Spider Network Operations".

Ce script :
1. Appelle les 3 agents Spider (Affiliate / Media / Digital Products) via l'API Groq.
2. Enregistre chaque résultat dans un fichier JSON (data/spider_log.json) qui reste
   dans le dépôt Git (persistance gratuite, sans base de données externe).
3. Envoie un rapport récapitulatif par email via Gmail (SMTP + App Password).

Conçu pour tourner via GitHub Actions, une fois par heure (voir le fichier .yml associé).
"""

import os
import json
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from groq import Groq

# ---------------------------------------------------------------------------
# Configuration (toutes les valeurs sensibles viennent des variables d'env /
# GitHub Secrets — ne jamais les écrire en dur ici)
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)
MODEL = "llama-3.1-8b-instant"
LOG_PATH = "data/spider_log.json"

client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------------------------
# Prompts système des 3 agents (basés sur le cahier des charges)
# ---------------------------------------------------------------------------
AGENTS = {
    "Affiliate Spider": (
        "You are an autonomous market analyst and affiliate strategist. "
        "Identify one high-potential micro-niche opportunity right now, a traffic "
        "acquisition angle, and one actionable next step for North African / global "
        "digital markets. Keep it under 120 words, structured with short headers."
    ),
    "Media Spider": (
        "You are a viral growth hacker and direct-response copywriter. "
        "Generate one psychological ad hook and a 3-beat short-form video (Reel/TikTok) "
        "outline designed to stop the scroll. Keep it under 120 words, structured with "
        "short headers."
    ),
    "Digital Products Spider": (
        "You are a digital product architect and SEO content strategist. "
        "Propose one micro digital-product idea (ebook/mini-course) with a 3-module "
        "outline and one pricing suggestion. Keep it under 120 words, structured with "
        "short headers."
    ),
}


def run_agent(name: str, system_prompt: str) -> str:
    """Appelle un agent Spider et renvoie son texte, avec gestion d'erreur robuste."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Give today's hourly signal."},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # on ne casse jamais tout le run pour un agent en panne
        return f"[ERREUR {name}: {exc}]"


def load_log() -> list:
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_log(entries: list) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def send_email(subject: str, body: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    results = {}
    for name, prompt in AGENTS.items():
        results[name] = run_agent(name, prompt)

    log = load_log()
    log.append({"timestamp": timestamp, "results": results})
    # on garde uniquement les 500 dernières entrées pour que le fichier reste léger
    log = log[-500:]
    save_log(log)

    total_runs = len(log)
    body_lines = [
        f"Rapport Spider Network — {timestamp}",
        f"Nombre total de cycles enregistrés : {total_runs}",
        "",
    ]
    for name, text in results.items():
        body_lines.append(f"--- {name} ---")
        body_lines.append(text)
        body_lines.append("")

    send_email(
        subject=f"[Spider Network] Rapport horaire — {timestamp[:16]}",
        body="\n".join(body_lines),
    )
    print("Cycle terminé et email envoyé.")


if __name__ == "__main__":
    main()
