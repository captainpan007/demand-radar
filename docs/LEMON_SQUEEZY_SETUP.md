# Lemon Squeezy Setup

## Create Product

1. Log in to https://app.lemonsqueezy.com
2. Store → Products → Add Product
3. Name: "Demand Radar Pro"
4. Pricing: Subscription → $9/month
5. After creating, go to product page → copy the Checkout URL

## Configure Webhook

1. Settings → Webhooks → Add Endpoint
2. URL: `https://your-domain.com/webhook/lemon`
3. Select events:
   - `subscription_created`
   - `subscription_updated`
   - `subscription_expired`
4. Copy the Signing Secret

## Environment Variables

```bash
# Windows
set LEMON_SQUEEZY_CHECKOUT_URL=https://your-store.lemonsqueezy.com/checkout/buy/xxx
set LEMON_SQUEEZY_SIGNING_SECRET=your_signing_secret_here

# Linux/Mac
export LEMON_SQUEEZY_CHECKOUT_URL=https://your-store.lemonsqueezy.com/checkout/buy/xxx
export LEMON_SQUEEZY_SIGNING_SECRET=your_signing_secret_here
```

## Checkout URL with Pre-fill

The pricing page automatically appends the user's email to the checkout URL:
`{checkout_url}?checkout[custom][user_email]={email}`

This allows the webhook to match the Lemon Squeezy subscription to the correct user.
