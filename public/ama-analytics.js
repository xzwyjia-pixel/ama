/**
 * AMA Analytics — Lightweight conversion tracking
 * Tracks page views, events, and sends to /api/leads as analytics events.
 * Zero external dependencies. No cookies. Privacy-first.
 */
(function() {
  const SESSION = 'ama_' + Date.now().toString(36);
  const API = '/api/leads';
  let pageViewSent = false;

  function send(event, data) {
    const payload = {
      session: SESSION,
      event: event,
      page: location.pathname,
      referrer: document.referrer || 'direct',
      timestamp: new Date().toISOString(),
      screenSize: screen.width + 'x' + screen.height,
      language: navigator.language,
      ...data
    };

    // Fire-and-forget to analytics endpoint
    try {
      fetch(API, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          email: 'analytics@ama.internal',
          source: 'analytics',
          monthlySpend: 0,
          monthlyWaste: 0,
          wastePct: '0%',
          yearlySavings: 0,
          teamSize: 0,
          ...payload
        }),
        keepalive: true
      }).catch(() => {});
    } catch(e) {}

    // Also log to console in dev
    if (location.hostname === 'localhost') {
      console.log('[AMA Analytics]', event, data);
    }
  }

  // Page view
  if (!pageViewSent) {
    send('pageview', {title: document.title});
    pageViewSent = true;
  }

  // Track outbound clicks (Stripe, Store, etc.)
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href') || '';
    if (href.includes('stripe.com') || href.includes('buy.stripe.com')) {
      send('click_stripe', {url: href});
    }
    if (href.includes('/store')) {
      send('click_store', {});
    }
    if (href.includes('/enterprise')) {
      send('click_enterprise', {});
    }
    if (href.includes('/calculator')) {
      send('click_calculator', {});
    }
  });

  // Track form submissions
  document.addEventListener('submit', function(e) {
    const form = e.target.closest('form');
    if (!form) return;
    const emailInput = form.querySelector('input[type="email"]');
    send('form_submit', {
      formId: form.id || 'unknown',
      hasEmail: !!emailInput
    });
  });

  // Expose for manual tracking
  window.amaTrack = function(event, data) {
    send(event, data);
  };

  // Track calculator interactions
  if (location.pathname.includes('calculator') || location.pathname === '/') {
    let sliderTouched = false;
    document.addEventListener('input', function(e) {
      if (e.target.type === 'range' && !sliderTouched) {
        sliderTouched = true;
        send('calculator_interact', {});
      }
    }, {once: false});
  }
})();
