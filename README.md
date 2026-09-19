# 🕷️ Spider Network (شبكة العناكب)

نظام وكلاء متعدد التخصصات يعمل في الخلفية: خمسة عناكب متخصصة + عنكبوت ملكة (Queen)
لتنسيق المهام عبر LangGraph.

## العناكب

| العنكبوت | التخصص |
|---|---|
| **Affiliate** | تحليل الأسواق، النيتشات، استراتيجيات الأفلييت (عربي/فرنسي/إنجليزي) |
| **Media** | هوكس إعلانية، سكريبتات Reels/TikTok، funnels |
| **Digital Products** | كتب إلكترونية، دورات مصغرة، تسعير، SEO |
| **Engineering** | تصميم قطع بأبعاد حقيقية + حسابات فيزياء (beam bending) + OpenSCAD |
| **Electronics** | دوائر بقوانين Ohm حقيقية (LED، مقاومات، عمر البطارية) |

الملكة (Queen) تحلل المهمة وتقرر أي العناكب تعمل عليها (بالتوازي)، ثم تجمع التقرير.

## التشغيل المحلي (Streamlit)

```bash
pip install -r requirements.txt
echo 'GROQ_API_KEY = "your-key"' > .streamlit/secrets.toml
streamlit run app.py
```

## التشغيل الخلفي (بدون فتح التطبيق)

```bash
export GROQ_API_KEY=...
python monitor.py --task "مهمتك هنا"
```

لإيقاف الإيميل: `--no-email`.

## GitHub Actions (كل ساعة)

الملف `.github/workflows/spider-monitor.yml` يشغل العناكب كل ساعة، يسجل النتائج
في `data/spider_log.json` (commit تلقائي)، ويرسل تقريراً بالبريد.

### الأسرار المطلوبة (Repository Secrets)

في GitHub: Settings → Secrets and variables → Actions:

| Secret | الوصف |
|---|---|
| `GROQ_API_KEY` | مفتح Groq من console.groq.com |
| `GMAIL_USER` | بريد Gmail المرسل |
| `GMAIL_APP_PASSWORD` | App Password (من myaccount.google.com/apppasswords) |
| `RECIPIENT_EMAIL` | البريد المستلم للتقارير |

> ⚠️ لا تضع أي سر في الكود أو المحادثات — فقط في Secrets.

## ملاحظات أمان مهمة

- حسابات Engineering Spider **drafts**: كل الأرقام تأتي من محرك حساب حقيقي
  (وليس من النموذج)، لكن أي تصنيع فعلي يتطلب مراجعة مهندس مرخص.
- الإلكترونيات: القيم محسوبة بقوانين Ohm الفعلية مع هامش أمان.
