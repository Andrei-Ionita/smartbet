# 🚀 SmartBet Deployment Checklist

Use this checklist to ensure smooth deployment.

---

## Pre-Deployment ✅

### Code Preparation
- [ ] All code committed to GitHub
- [ ] Latest changes pushed to `main` branch
- [ ] No sensitive data in code (API keys, passwords, etc.)
- [ ] `.env` file is in `.gitignore`
- [ ] `db.sqlite3` is in `.gitignore`

### Configuration Files
- [ ] `requirements.txt` includes all production dependencies
- [ ] `render.yaml` configured correctly
- [ ] `build.sh` is executable and tested
- [ ] `frontend/vercel.json` configured
- [ ] `frontend/next.config.ts` updated with API URL handling

### Environment Variables Ready
- [ ] SportMonks API token obtained
- [ ] Have list of all required environment variables

---

## Backend Deployment (Render) 🐍

### Account Setup
- [ ] Render account created
- [ ] GitHub connected to Render
- [ ] Repository access granted

### Service Creation
- [ ] Blueprint deployed from `render.yaml`
- [ ] Web service created successfully
- [ ] PostgreSQL database provisioned

### Environment Variables
- [ ] `DEBUG` = `False`
- [ ] `DJANGO_SECRET_KEY` (auto-generated)
- [ ] `DATABASE_URL` (auto-set)
- [ ] `ALLOWED_HOSTS` configured
- [ ] `SPORTMONKS_TOKEN` added
- [ ] `SPORTMONKS_API_TOKEN` added
- [ ] `FRONTEND_URL` (add after frontend deployed)

### Build & Deploy
- [ ] Build completed successfully
- [ ] Migrations ran without errors
- [ ] Static files collected
- [ ] Service is running
- [ ] Health check endpoint works: `/api/health/`

### Post-Deployment
- [ ] Django admin accessible: `/admin/`
- [ ] Superuser created via Shell
- [ ] API endpoints responding correctly

---

## Frontend Deployment (Vercel) ⚡

### Account Setup
- [ ] Vercel account created
- [ ] GitHub connected to Vercel

### Project Import
- [ ] Repository imported
- [ ] `frontend` folder selected as root directory
- [ ] Framework detected as Next.js

### Environment Variables
- [ ] `NEXT_PUBLIC_API_URL` set to Render backend URL

### Build & Deploy
- [ ] Build completed successfully
- [ ] No build errors
- [ ] Site is live

### Post-Deployment
- [ ] Frontend loads correctly
- [ ] Can connect to backend API
- [ ] No CORS errors in console

---

## Integration & CORS 🔗

### Update Backend CORS
- [ ] Returned to Render dashboard
- [ ] Updated `FRONTEND_URL` with Vercel URL
- [ ] Updated `ALLOWED_HOSTS` to include both domains
- [ ] Backend redeployed with new settings

### Test Integration
- [ ] Frontend can fetch data from backend
- [ ] Predictions display correctly
- [ ] No CORS errors
- [ ] All API calls working

---

## Production Verification ✨

### Functionality Tests
- [ ] Homepage loads
- [ ] Predictions fetched from SportMonks
- [ ] Filters work correctly
- [ ] Match details page loads
- [ ] Bankroll management works
- [ ] Performance tracking displays

### Performance
- [ ] Page load times acceptable
- [ ] API response times reasonable
- [ ] No console errors
- [ ] No broken images/links

### Security
- [ ] `DEBUG = False` verified
- [ ] HTTPS working on both domains
- [ ] No sensitive data exposed
- [ ] Admin panel secured
- [ ] CORS properly configured

---

## Optional Enhancements 🎯

### Monitoring
- [ ] Error tracking setup (Sentry, etc.)
- [ ] Uptime monitoring (UptimeRobot)
- [ ] Analytics installed (Google Analytics)

### Performance
- [ ] Consider upgrading to Render Starter ($7/mo) for always-on
- [ ] Setup Redis for caching (if needed)

### Domain
- [ ] Custom domain purchased
- [ ] DNS configured for frontend
- [ ] DNS configured for backend
- [ ] SSL certificates active

### Automation
- [ ] Cron jobs configured for data updates
- [ ] Auto-deployment enabled for both platforms
- [ ] Backup strategy in place

---

## 🎉 Deployment Complete!

**Your URLs:**
- Frontend: `https://__________.vercel.app`
- Backend: `https://__________.onrender.com`
- Admin: `https://__________.onrender.com/admin/`

**Credentials:**
- Admin username: `__________`
- Admin password: `__________` (stored securely)

**Next Steps:**
1. Monitor logs for 24-48 hours
2. Test all features thoroughly
3. Announce launch! 🚀

---

**Date Deployed:** ___________
**Deployed By:** ___________
**Notes:** ___________

