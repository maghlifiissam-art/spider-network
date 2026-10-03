# Reels app roadmap (zero spend, free tiers)
Done: v0 feed PWA (4 sections), v0 closed groups + Jitsi calls (front-end demo).
Next, in order:
1. Supabase backend: accounts, group admin role, membership, posts, shared video storage. Keys never in the repo.
2. User-approved additions (3 Oct 2026):
   a. Low-data mode: lower-quality video, lazy/preload only the next reel, data saver toggle.
   b. Referral system: personal invite link, points per signed-up friend.
   c. AI captions/translation on reels (free Workers AI), so Moroccan content reaches abroad.
3. News/Courses auto-fill from the spiders; ads submit form.
4. Marketplace (user request 3 Oct): Shop section to list and sell products; sellers post product reels; sponsored/ad reels inserted in the main feed (labelled 'Sponsored'). Payments: no card processing built by us. Start with cash on delivery and order messages to the seller; later a free-to-integrate gateway (e.g. CMI/PayPal links), each decided by the user since money and legal terms are his.
Later (proposed, not approved): in-app course store, publisher analytics.

## Monetization (user direction, 3 Oct 2026)
1. Paid sponsored reels from advertisers (labelled Sponsored). Works from the start: price per slot/week, advertiser pays the user directly at first.
2. Google ads (AdSense-style): only after real traffic. Google needs an approved account, a real domain/content and an audience; the free GitHub Pages address is not enough. Apply once there are steady users; the account and terms are the user's decision.
No ads in the app before the audience exists.

## Built-in AI assistant (user request, 3 Oct 2026)
Helps creators with ideas, scripts, captions and hashtags in Arabic/Darija/French/English. Free tier only: Cloudflare Workers AI through a Worker (no key in the browser), with a per-user daily limit. Same engine later powers reel captions/translation. Starts after the backend (needs accounts for limits).

## Identity and admin (user direction, 3 Oct 2026)
Look: light violet + gold. Admin dashboard (dashboard.html): money in, money out, creator payouts, split control. Default split 70% creator / 30% platform, adjustable. Real data after the backend; the access must be admin-only then (demo page is open).


## Launch plan (fast feedback)
Start only once the full flow works end to end (login, channel, upload, follow, admin dashboard).
1. Morocco first: the owner's network and Darija content. Seed 10-20 creators, collect feedback in the first 2 weeks.
2. Egypt next: largest Arabic audience with high engagement. Same creator seeding approach, Arabic UI polish.
3. Gulf later, once there is enough creator content to show.
Support for all: low-data mode, referral codes (invite a friend), short feedback form inside the app.
Metrics: sign-ups, creators with a channel, reels posted, follows, day-7 return rate.
Money and legal choices (ads, payouts, terms) go to the owner first.
