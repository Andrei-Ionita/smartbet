# ⚡ SmartBet - 20-Minute Render Deployment

Deploy both frontend and backend on Render in 20 minutes.

**✨ No timeout limits!** Perfect for long-running API requests.

---

## 🚀 Step 1: Push to GitHub (2 min)

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

---

## 🔧 Step 2: Deploy with Blueprint (5 min)

1. Go to https://render.com → Sign up with GitHub
2. Click **"New +"** → **"Blueprint"**
3. Select your **`smartbet`** repository
4. Render detects `render.yaml` and creates:
   - ✅ Backend (Django)
   - ✅ Frontend (Next.js)
   - ✅ Database (PostgreSQL)

---

## ⚙️ Step 3: Set Environment Variables (3 min)

### Backend (smartbet-backend)

Click service → **Environment** tab → Add:

- `SPORTMONKS_TOKEN` = `your-token`
- `SPORTMONKS_API_TOKEN` = `your-token`
- *(Leave other variables as-is)*

### Frontend (smartbet-frontend)

- *(Leave as-is for now - we'll update after deployment)*

Click **"Apply"** → Wait 10-15 minutes for deployment

---

## 🔗 Step 4: Connect Services (5 min)

After deployment, get your URLs:

1. **Backend:** `https://smartbet-backend-XXXXX.onrender.com`
2. **Frontend:** `https://smartbet-frontend-XXXXX.onrender.com`

### Update Backend

Go to **smartbet-backend** → **Environment** → Add:

- `FRONTEND_URL` = `https://smartbet-frontend-XXXXX.onrender.com`
- `ALLOWED_HOSTS` = `smartbet-backend-XXXXX.onrender.com,smartbet-frontend-XXXXX.onrender.com`

Save → Backend redeploys (~2 min)

### Update Frontend

Go to **smartbet-frontend** → **Environment** → Add:

- `NEXT_PUBLIC_API_URL` = `https://smartbet-backend-XXXXX.onrender.com`

Save → Frontend redeploys (~2 min)

---

## ✅ Step 5: Test (3 min)

1. **Backend Health:** Visit `https://smartbet-backend-XXXXX.onrender.com/api/health/`
   - Should see: `{"status": "healthy", "service": "smartbet-backend"}`

2. **Frontend:** Visit `https://smartbet-frontend-XXXXX.onrender.com`
   - Should load homepage

3. **Check Console:** Press F12 → No CORS errors

---

## 🔐 Step 6: Create Admin User (2 min)

1. Go to **smartbet-backend** → **Shell** tab
2. Run:
   ```bash
   python manage.py createsuperuser
   ```
3. Set username/password
4. Visit: `https://smartbet-backend-XXXXX.onrender.com/admin/`

---

## 🎉 You're Live!

**Your URLs:**
- Frontend: `https://smartbet-frontend-XXXXX.onrender.com`
- Backend: `https://smartbet-backend-XXXXX.onrender.com`
- Admin: `https://smartbet-backend-XXXXX.onrender.com/admin/`

**Current Plan: FREE ($0/month)**
- Services sleep after 15 min inactivity
- First request takes ~30s to wake up

**Upgrade to Always-On ($21/month total):**
1. Each service → **Settings** → **Pricing**
2. Select **"Starter"** ($7/month per service)
3. Database → **"Starter"** ($7/month)

---

## 🐛 Troubleshooting

**Backend won't start:**
- Check **Logs** tab for errors
- Verify `SPORTMONKS_TOKEN` is set
- Try: **Manual Deploy** → **"Clear build cache & deploy"**

**Frontend won't connect:**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check `FRONTEND_URL` and `ALLOWED_HOSTS` in backend

**CORS errors:**
- Update `FRONTEND_URL` in backend
- Update `ALLOWED_HOSTS` in backend
- Save and redeploy

---

## 🔄 Auto-Deploy Enabled

Push to GitHub → Render auto-deploys:

```bash
git add .
git commit -m "Update app"
git push origin main
```

Both services update automatically in 3-5 minutes.

---

## 📚 Full Documentation

For detailed guides:
- **`RENDER_DEPLOYMENT_GUIDE.md`** - Complete step-by-step guide
- **`env.example`** - All environment variables
- **`DEPLOYMENT_SUMMARY.md`** - Configuration overview

---

## 💰 Cost Summary

| Tier | Backend | Frontend | Database | Total |
|------|---------|----------|----------|-------|
| **Free** | $0 | $0 | $0 | **$0/month** |
| **Production** | $7 | $7 | $7 | **$21/month** |

---

## ✨ Benefits

- ✅ **No timeout limits** - Process as long as you need
- ✅ **Single platform** - Everything in one place
- ✅ **Auto HTTPS** - SSL certificates included
- ✅ **Auto-deploy** - Push to deploy
- ✅ **No configuration** - Works out of the box

---

**Need help?** Check `RENDER_DEPLOYMENT_GUIDE.md` for detailed troubleshooting.

**Good luck! 🚀**

