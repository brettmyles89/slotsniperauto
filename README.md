# SlotSniper & TrialKiller

Real-time **slot alerts** (SlotSniper) and **free-trial reminders** (TrialKiller), delivered to **Telegram + Email** with Stripe checkout and auto-activation.

- Live: **https://slotsniper.app** • **https://trialkiller.app**
- Bots: **t.me/SlotSniperAlertsBot** • **t.me/TrialKillerBot**
- Launch promo (example): `LAUNCH20` (20% off)

---

## ✨ What’s inside

- **Flask app** (single repo, host-aware routing for both brands)
- **Stripe Checkout + Webhooks** → license activation
- **Telegram + Email (Resend)** alerts
- **SQLite (core.db)** for licenses & events
- **Two brands** in one deployment (domain-aware)
- **Growth blitz** scripts: 1000-post, 72h plan (Reddit/Discord/Telegram/IH/PH) — *free stack*

---

## 🧭 Plans & Pricing (current)

**SlotSniper** *(one-time 7-day passes)*
- Basic — **$7** (7-day pass)
- Pro — **$15** (7-day pass)

**TrialKiller**
- Pro Monthly — **$3.99 / month** (subscription)
- Pro Lifetime — **$14.99** (one-time)

**Frontend plan codes** your buttons send to `/api/checkout`:
