/**
 * AMA Lead Capture API — Vercel Serverless Function
 *
 * GET  /api/leads       → list all leads (admin)
 * POST /api/leads       → capture new lead from calculator
 * PUT  /api/leads       → update lead status (approve/reject)
 *
 * Storage: ephemeral (serverless memory + JSON blob).
 * For production persistence, add Vercel KV or Upstash Redis.
 */

// In-memory store (survives between invocations while function is warm)
let leads = [];
let leadIdCounter = 0;

// Try to recover from previous runs via global
if (global.__AMA_LEADS__) {
  leads = global.__AMA_LEADS__;
  leadIdCounter = global.__AMA_LEAD_ID__ || 0;
}

function persist() {
  global.__AMA_LEADS__ = leads;
  global.__AMA_LEAD_ID__ = leadIdCounter;
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

function generateReport(lead) {
  return {
    subject: `Your AI Waste Report — $${lead.monthlyWaste?.toLocaleString() || 'N/A'}/mo wasted`,
    summary: `
AI Cost Analysis for ${lead.company || 'Your Company'}
============================================
Team Size:           ${lead.teamSize || '?'} developers
Monthly AI Spend:    $${lead.monthlySpend?.toLocaleString() || '?'}
Monthly Waste:       $${lead.monthlyWaste?.toLocaleString() || '?'} (${lead.wastePct || '?'}% of spend)
Yearly Savings (AMA): $${lead.yearlySavings?.toLocaleString() || '?'}

Top Waste Sources:
  1. Duplicate Calls:     $${lead.dupWaste?.toLocaleString() || '?'}
  2. Overqualified Models: $${lead.overWaste?.toLocaleString() || '?'}
  3. Cache Misses:         $${lead.cacheWaste?.toLocaleString() || '?'}
  4. Zombie Agents:        $${lead.zombieWaste?.toLocaleString() || '?'}

Get AMA: pip install ama-core  |  https://github.com/ama-agent/ama
`,
    installCommand: 'pip install ama-core && ama scan && ama start',
    onboardingUrl: 'https://ama-agent-store.vercel.app/store',
  };
}

export default async function handler(request) {
  const { method, url } = request;
  const parsedUrl = new URL(url, 'http://localhost');
  const path = parsedUrl.pathname;

  // CORS preflight
  if (method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  }

  // GET /api/leads — list all leads
  if (method === 'GET') {
    const status = parsedUrl.searchParams.get('status');
    let result = leads;
    if (status) {
      result = leads.filter(l => l.status === status);
    }
    return jsonResponse({
      total: result.length,
      pending: leads.filter(l => l.status === 'new').length,
      approved: leads.filter(l => l.status === 'approved').length,
      leads: result.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt)),
    });
  }

  // POST /api/leads — capture new lead
  if (method === 'POST') {
    const body = await request.json().catch(() => ({}));

    leadIdCounter++;
    const lead = {
      id: `lead_${String(leadIdCounter).padStart(4, '0')}`,
      email: body.email || 'unknown',
      company: body.company || '',
      teamSize: body.teamSize || 0,
      monthlySpend: body.monthlySpend || 0,
      monthlyWaste: body.monthlyWaste || 0,
      wastePct: body.wastePct || '0%',
      yearlySavings: body.yearlySavings || 0,
      dupWaste: body.dupWaste || 0,
      overWaste: body.overWaste || 0,
      cacheWaste: body.cacheWaste || 0,
      zombieWaste: body.zombieWaste || 0,
      source: body.source || 'calculator',
      status: 'new',
      createdAt: new Date().toISOString(),
      approvedAt: null,
      notes: '',
    };

    leads.push(lead);

    // Keep only last 200 leads to avoid memory bloat
    if (leads.length > 200) {
      leads = leads.slice(-200);
    }

    persist();

    const report = generateReport(lead);

    console.log(`[AMA Lead] New lead: ${lead.email} | Waste: $${lead.monthlyWaste} | Savings: $${lead.yearlySavings}`);

    return jsonResponse({
      success: true,
      lead,
      report,
      message: `Lead captured! ${lead.yearlySavings > 10000 ? '🔥 HOT LEAD' : ''} ${lead.email} could save $${lead.yearlySavings}/year`,
    }, 201);
  }

  // PUT /api/leads — update lead status
  if (method === 'PUT') {
    const body = await request.json().catch(() => ({}));
    const { id, status, notes } = body;

    const lead = leads.find(l => l.id === id);
    if (!lead) {
      return jsonResponse({ error: 'Lead not found' }, 404);
    }

    if (status) {
      lead.status = status;
      if (status === 'approved') {
        lead.approvedAt = new Date().toISOString();
      }
    }
    if (notes !== undefined) lead.notes = notes;

    persist();

    console.log(`[AMA Lead] ${lead.email} → ${lead.status}`);

    const report = lead.status === 'approved' ? generateReport(lead) : null;

    return jsonResponse({
      success: true,
      lead,
      report,
      action: lead.status === 'approved' ? 'onboarding_ready' : 'status_updated',
    });
  }

  return jsonResponse({ error: 'Method not allowed' }, 405);
}
