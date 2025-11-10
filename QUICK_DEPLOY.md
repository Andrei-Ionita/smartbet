# ⚡ SmartBet - 30-Minute Deployment Guide

**Your app is production-ready!** Deploy in 30 minutes by following these steps.

---

## 🚀 Step 1: Push to GitHub (2 min)

```bash
git add .
git commit -m "Production ready for deployment"
git push origin main
```

---

## 🔧 Step 2: Deploy Backend to Render (10 min)

1. Go to https://render.com → Sign up with GitHub
2. Click **"New +"** → **"Blueprint"**
3. Connect your `smartbet` repository
4. Render auto-detects `render.yaml` and creates:
   - Web service (Django)
   - PostgreSQL database

5. **Set Environment Variables:**
   - `DEBUG` = `False`
   - `SPORTMONKS_TOKEN` = `your-token-here`
   - `SPORTMONKS_API_TOKEN` = `your-token-here`
   - `ALLOWED_HOSTS` = *leave blank for now*
   - `FRONTEND_URL` = *leave blank for now*

6. Click **"Apply"** → Wait for deployment (~10 min)

7. **Copy your backend URL:** `https://smartbet-XXXXX.onrender.com`

---

## ⚡ Step 3: Deploy Frontend to Vercel (3 min)

1. Go to https://vercel.com → Sign up with GitHub
2. Click **"Add New"** → **"Project"**
3. Import your `smartbet` repository
4. **Root Directory:** Select `frontend` folder
5. **Environment Variables:**
   - `NEXT_PUBLIC_API_URL` = `https://smartbet-XXXXX.onrender.com` (your backend URL from Step 2)

6. Click **"Deploy"** → Wait (~3 min)

7. **Copy your frontend URL:** `https://smartbet-XXXXX.vercel.app`

---

## 🔗 Step 4: Connect Frontend & Backend (5 min)

1. Go back to **Render dashboard**
2. Click your backend service → **"Environment"**
3. Update these variables:
   - `FRONTEND_URL` = `https://smartbet-XXXXX.vercel.app` (from Step 3)
   - `ALLOWED_HOSTS` = `smartbet-XXXXX.onrender.com,smartbet-XXXXX.vercel.app`

4. Save → Backend will redeploy (~2 min)

---

## ✅ Step 5: Test Your Deployment (5 min)

1. **Test Backend Health:**
   - Visit: `https://smartbet-XXXXX.onrender.com/api/health/`
   - Should see: `{"status": "healthy", "service": "smartbet-backend"}`

2. **Test Frontend:**
   - Visit: `https://smartbet-XXXXX.vercel.app`
   - Should load homepage

3. **Test Integration:**
   - Check browser console (F12) for errors
   - Verify predictions load

---

## 🔐 Step 6: Create Admin User (5 min)

1. Go to Render dashboard → Your backend service
2. Click **"Shell"** tab
3. Run:
   ```bash
   python manage.py createsuperuser
   ```
4. Enter username, email, password
5. Test: `https://smartbet-XXXXX.onrender.com/admin/`

---

## 🎉 You're Live!

**Your URLs:**
- Frontend: `https://smartbet-XXXXX.vercel.app`
- Backend: `https://smartbet-XXXXX.onrender.com`
- Admin: `https://smartbet-XXXXX.onrender.com/admin/`

---

## 💰 Current Plan: FREE

- Render: Free tier (sleeps after 15 min)
- Vercel: Free tier
- **Cost: $0/month**

**To keep backend always-on:** Upgrade to Render Starter ($7/month)

---

## 🐛 Troubleshooting

**Backend won't start:**
- Check Render logs → "Logs" tab
- Verify environment variables are set

**Frontend can't connect:**
- Check `NEXT_PUBLIC_API_URL` in Vercel
- Verify `FRONTEND_URL` in Render
- Check CORS errors in browser console

**CORS errors:**
- Update `FRONTEND_URL` in Render
- Update `ALLOWED_HOSTS` in Render
- Redeploy backend

---

## 📚 Full Documentation

For detailed guides:
- **`DEPLOYMENT_GUIDE.md`** - Complete step-by-step guide
- **`DEPLOYMENT_CHECKLIST.md`** - Track your progress
- **`PRODUCTION_READY.md`** - Configuration overview
- **`DEPLOYMENT_SUMMARY.md`** - What was configured

---

## ⚙️ Next Steps (Optional)

- [ ] Setup uptime monitoring (UptimeRobot)
- [ ] Add custom domain
- [ ] Setup error tracking (Sentry)
- [ ] Configure analytics
- [ ] Upgrade to paid tier for always-on backend

---

**Need help?** Check the full documentation or platform support.

**Good luck! 🚀**

