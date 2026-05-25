/**
 * PostHog Analytics — PuenteWorks + Kyanite Labs
 *
 * Initializes PostHog with session replay and web analytics.
 * Automatically captures click events from elements tagged with
 * data-analytics-event attributes.
 *
 * Attributes consumed:
 *   data-analytics-event  — event name (e.g. "click_paid_readiness_cta")
 *   data-brand-surface   — "puenteworks" or "kyanite" (for filtering in dashboard)
 *   data-language         — "en" or "es"
 *   data-cta-location     — where on the page the CTA sits (e.g. "hero_primary")
 *   data-offer-path       — service path if applicable (e.g. "readiness")
 */
(() => {
  // PostHog JS snippet
  !((t,e)=> {var o,n,p,r;e.__SV||(window.posthog && window.posthog.__loaded)||(window.posthog=e,e._i=[],e.init=(i,s,a)=> {function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=(t)=> {var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=()=> u.toString(1)+".people (stub)",o="init os ds Ie us vs ss ls capture calculateEventProperties register register_once register_for_session unregister unregister_for_session ws getFeatureFlag getFeatureFlagPayload getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey displaySurvey cancelPendingSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException startExceptionAutocapture stopExceptionAutocapture loadToolbar get_property getSessionProperty bs ps createPersonProfile setInternalOrTestUser ys es $s opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing get_explicit_consent_status is_capturing clear_opt_in_out_capturing cs debug M gs getPageViewId captureTraceFeedback captureTraceMetric Qr".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)})(document,window.posthog||[]);

  posthog.init('phc_xCWVuCx8TVyi3YUzfVNX8BwznXbSvN9jesgEMkNs7Bde', {
    api_host: 'https://us.i.posthog.com',
    defaults: '2026-01-30',
    session_replay: true,
    capture_pageview: true,
    capture_pageleave: true,
  });

  /**
   * Wire up data-analytics-event click tracking.
   * This reads the data-* attributes you already have on CTAs
   * and sends them as structured PostHog events.
   */
  document.addEventListener('click', (e) => {
    var el = e.target.closest('[data-analytics-event]');
    if (!el) return;

    var eventName = el.getAttribute('data-analytics-event');
    if (!eventName) return;

    var props = {
      brand_surface: el.getAttribute('data-brand-surface') || 'unknown',
      language: el.getAttribute('data-language') || document.documentElement.lang || 'unknown',
      cta_location: el.getAttribute('data-cta-location') || 'unknown',
      offer_path: el.getAttribute('data-offer-path') || null,
      link_url: el.href || null,
      link_text: (el.textContent || '').trim().substring(0, 200),
      page_path: window.location.pathname,
    };

    // Remove null props for cleanliness
    Object.keys(props).forEach((k) => {
      if (props[k] === null) delete props[k];
    });

    posthog.capture(eventName, props);
  }, { passive: true });
})();
