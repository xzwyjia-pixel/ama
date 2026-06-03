// Create Stripe Payment Links via API
const https = require('https');
const readline = require('readline');

function stripeRequest(method, path, body, apiKey) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.stripe.com', path, method,
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', d => data += d);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(data) }); }
        catch { resolve({ status: res.statusCode, data }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(new URLSearchParams(body).toString());
    req.end();
  });
}

async function main() {
  // Read API key from env var
  const apiKey = process.env.STRIPE_KEY || '';
  if (!apiKey) {
    console.log('Set STRIPE_KEY env var and run again.');
    console.log('Example: set STRIPE_KEY=sk_live_xxx && node stripe-setup.js');
    process.exit(1);
  }

  if (!apiKey.startsWith('sk_')) {
    console.log('Invalid key. Must start with sk_');
    process.exit(1);
  }

  console.log('\nCreating 3 subscription products + payment links...\n');

  const plans = [
    { name: 'AI Content Department', price: 49900, desc: '30 long-form articles/month. 5-Agent pipeline. 24h turnaround.' },
    { name: 'AI Support Department', price: 79900, desc: '3-tier Agent escalation. 7x24 coverage. Auto knowledge base.' },
    { name: 'AI Analytics Department', price: 29900, desc: '5-Agent parallel analysis. Weekly reports. PDF/PPT/Dashboard.' },
  ];

  const results = [];

  for (const plan of plans) {
    console.log(`Creating: ${plan.name}...`);

    // Step 1: Create Product
    const productResp = await stripeRequest('POST', '/v1/products', {
      name: plan.name,
      description: plan.desc,
      'metadata[category]': 'ai-department',
    }, apiKey);

    if (!productResp.data.id) {
      console.log(`  Product failed:`, JSON.stringify(productResp.data).substring(0, 200));
      continue;
    }
    const productId = productResp.data.id;

    // Step 2: Create Price (recurring)
    const priceResp = await stripeRequest('POST', '/v1/prices', {
      product: productId,
      'unit_amount': plan.price,
      currency: 'usd',
      'recurring[interval]': 'month',
      'recurring[interval_count]': 1,
    }, apiKey);

    if (!priceResp.data.id) {
      console.log(`  Price failed:`, JSON.stringify(priceResp.data).substring(0, 200));
      continue;
    }
    const priceId = priceResp.data.id;

    // Step 3: Create Payment Link
    const linkResp = await stripeRequest('POST', '/v1/payment_links', {
      'line_items[0][price]': priceId,
      'line_items[0][quantity]': 1,
      'after_completion[type]': 'redirect',
      'after_completion[redirect][url]': 'https://agent-business-xi.vercel.app?success=true',
    }, apiKey);

    if (linkResp.data.url) {
      console.log(`  ✅ ${plan.name}: ${linkResp.data.url}`);
      results.push({ name: plan.name, url: linkResp.data.url, price: plan.price });
    } else {
      console.log(`  Link failed:`, JSON.stringify(linkResp.data).substring(0, 200));
    }
  }

  console.log('\n=== COPY THESE INTO LANDING PAGE ===');
  results.forEach(r => {
    console.log(`// ${r.name}: ${r.url}`);
  });
  console.log('=====================================');
}

main().catch(e => console.error(e.message));
