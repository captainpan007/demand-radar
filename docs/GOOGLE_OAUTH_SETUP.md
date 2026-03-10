# Google OAuth Setup

## Steps

1. Go to https://console.cloud.google.com/apis/credentials
2. Create project "Demand Radar" (or use existing)
3. Configure OAuth consent screen:
   - User Type: External
   - App name: Demand Radar
   - Support email: your email
   - Scopes: email, profile, openid
4. Create OAuth 2.0 Client ID:
   - Type: Web application
   - Name: Demand Radar Web
   - Authorized redirect URIs:
     - `http://localhost:8000/auth/callback` (dev)
     - `https://your-domain.com/auth/callback` (prod — add after Railway deploy)
5. Copy Client ID and Client Secret

## Environment Variables

```bash
# Windows
set GOOGLE_CLIENT_ID=your_client_id_here
set GOOGLE_CLIENT_SECRET=your_client_secret_here

# Linux/Mac
export GOOGLE_CLIENT_ID=your_client_id_here
export GOOGLE_CLIENT_SECRET=your_client_secret_here
```
