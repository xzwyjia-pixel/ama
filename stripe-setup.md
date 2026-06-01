# AMA Stripe Setup — 5 Minutes to Accept Payments

## Step 1: Create Stripe Account (2 min)

1. Go to https://stripe.com
2. Click "Sign Up" — free, no monthly fees
3. Verify email
4. You don't need to complete full business verification to start
   (Stripe lets you test and receive payments in "test mode" immediately)

## Step 2: Create Payment Links (3 min)

Go to: Stripe Dashboard → Payments → Payment Links → Create payment link

### Create these 4 links:

| Product | Price | Type | Description |
|---------|-------|------|-------------|
| AMA Pro Report | $49.00 | One-time | Detailed AI agent diagnostic report |
| AMA Pro Monthly | $9.90 | Recurring (monthly) | Premium agent access + priority support |
| AMA Team | $49.00 | Recurring (monthly) | Up to 50 agents + Admin dashboard |
| AMA Enterprise | $999.00 | Recurring (monthly) | Unlimited agents + SSO + SLA |

### For each link:
1. Click "Create payment link"
2. Choose "Product or subscription"
3. Fill in name, price, description
4. Click "Create link"
5. Copy the URL (looks like: https://buy.stripe.com/xxx)

## Step 3: Paste Links into AMA

Open this file and replace the placeholder links:
`public/store.html` → search for `STRIPE_LINKS`

```javascript
const STRIPE_LINKS = {
  pro_monthly:  'https://buy.stripe.com/PASTE_YOUR_LINK_HERE',  // $9.90/mo
  pro_yearly:   'https://buy.stripe.com/PASTE_YOUR_LINK_HERE',  // $99/yr
  team_monthly: 'https://buy.stripe.com/PASTE_YOUR_LINK_HERE',  // $49/mo
  enterprise:   'https://buy.stripe.com/PASTE_YOUR_LINK_HERE',  // $999/mo
  report_pro:   'https://buy.stripe.com/PASTE_YOUR_LINK_HERE',  // $49 one-time
};
```

Also update in `public/index.html`:
Search for `YOUR_PRO_REPORT_LINK` and replace with your Stripe link.

## Step 4: Deploy

```bash
cd c:\Users\25454\业务中控台
vercel deploy public/ --prod
```

## Step 5: Test

1. Open https://ama-agent-store.vercel.app/calculator
2. Fill in some data, submit email
3. Click "Get Pro Report — $49"
4. It should open your Stripe checkout page
5. Use Stripe test card: 4242 4242 4242 4242, any future date, any CVC

## Step 6: Go Live

When ready to accept real payments:
1. Complete Stripe business verification (takes 1-2 days)
2. Switch from test mode to live mode in Stripe Dashboard
3. Update your Payment Links to "live" mode
4. Redeploy
