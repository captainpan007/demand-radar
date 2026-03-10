# Railway Deployment

## Steps

1. Push code: `git push origin main`
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Select `captainpan007/demand-radar`
4. Add environment variables in Railway dashboard:

| Variable | Required | Notes |
|----------|----------|-------|
| DEEPSEEK_API_KEY | Yes | AI scoring |
| GOOGLE_CLIENT_ID | Yes | OAuth |
| GOOGLE_CLIENT_SECRET | Yes | OAuth |
| SECRET_KEY | Yes | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| BASE_URL | Yes | Your Railway public URL, e.g. `https://demand-radar-xxx.up.railway.app` |
| LEMON_SQUEEZY_SIGNING_SECRET | Later | After Lemon Squeezy webhook setup |
| LEMON_SQUEEZY_CHECKOUT_URL | Later | After creating Lemon Squeezy product |
| PRODUCTHUNT_API_KEY | Optional | Product Hunt data source |

5. Railway auto-deploys from Dockerfile
6. Persistent volume mounts automatically at `/app/data` (SQLite lives here)

## Post-Deploy

1. Update Google OAuth redirect URI to include production URL:
   `https://your-domain.com/auth/callback`
2. Update Lemon Squeezy webhook URL to production URL:
   `https://your-domain.com/webhook/lemon`
3. (Optional) Add custom domain in Railway settings

## Manual Pipeline Run

```bash
curl -X POST https://your-domain.com/admin/run-pipeline
```

## Logs

View in Railway dashboard → Deployments → Logs
