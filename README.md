# 🚀 FRP Tracker – Deployment Guide

## Stack
- **Frontend**: Streamlit (free on Streamlit Community Cloud)
- **Backend/Auth/DB**: Supabase (free tier, data never deleted)
- **Deploy**: streamlit.io (free forever for public apps)

---

## Step 1: Supabase Setup (5 mins)

1. Go to https://supabase.com → Sign up (free)
2. Create a new project (name it `frp-tracker`)
3. Go to **SQL Editor** → Paste and run `supabase_setup.sql`
4. Go to **Project Settings → API**:
   - Copy **Project URL** → this is your `SUPABASE_URL`
   - Copy **anon public key** → this is your `SUPABASE_ANON_KEY`

---

## Step 2: Deploy on Streamlit Cloud (5 mins)

1. Push this folder to a **GitHub repo** (public or private)
2. Go to https://share.streamlit.io → Sign in with GitHub
3. Click **New App** → select your repo → set main file as `app.py`
4. Click **Advanced Settings → Secrets** and add:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
ADMIN_EMAIL = "admin@frp.in"
```

5. Click **Deploy** → your app is live!

---

## Step 3: Create Admin Account

1. Open your app URL
2. Click **Sign Up** tab
3. Sign up with the **exact email** you set as `ADMIN_EMAIL`
4. Login → you'll see the Admin Dashboard

---

## How It Works

### For 55 Founders (Users):
- Sign up with their email
- Set Company Name + Founder Name in sidebar
- Select the Friday date for that week
- Fill PSF → PMF → GTM → Revenue → Funding tabs
- Click **Save** on each phase
- Go to **Analytics** tab to see their dashboard
- **Download** as JSON or CSV
- Can **upload** a previous JSON to continue from where they left off (versioning)

### For Admin:
- Login with admin email
- See ALL companies listed with their overall score %
- Search by company or founder name
- Click **View →** on any company
- Select any week to see their dashboard for that specific week
- Full analytics view per company

---

## Will Data Be Lost When App Sleeps?

| Concern | Answer |
|---|---|
| Streamlit sleeps after inactivity? | ✅ Wakes up in ~30s. No data lost (data is in Supabase) |
| Supabase pauses after 7 days inactive? | ✅ Just pauses, never deletes. Wakes up on first request |
| Passwords forgotten? | ❌ Never. Stored in Supabase Auth |
| Free forever? | ✅ Yes, for 55 users + weekly entries |

**Pro tip**: Set up a free ping at https://cron-job.org to hit your Supabase URL once every 5 days — this keeps it active without ever pausing.

---

## Local Development

```bash
pip install -r requirements.txt

# Create .streamlit/secrets.toml
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "eyJ..."
ADMIN_EMAIL = "admin@frp.in"
EOF

streamlit run app.py
```

---

## File Structure
```
frp_app/
├── app.py                 ← Main Streamlit app
├── requirements.txt       ← Python dependencies
├── supabase_setup.sql     ← Run once in Supabase SQL editor
└── README.md              ← This file
```
