(function () {
  var receipt = { ready: false, source: 'liminal-sites-sensorium', error: null };
  window.__liminalSitesSensorium = receipt;

  function markError(error) {
    receipt.error = error && error.message ? error.message : String(error || 'unknown error');
    window.__liminalSitesSensorium = receipt;
    window.dispatchEvent(new CustomEvent('liminal-sites-sensorium-error', { detail: receipt }));
  }

  function currentScript() {
    return document.currentScript || document.querySelector('script[data-liminal-sites-sensorium]');
  }

  function configUrl(script) {
    if (script && script.getAttribute('data-config-url')) return script.getAttribute('data-config-url');
    if (script && script.src) return new URL('liminal-sensorium-config.json', script.src).href;
    return '/static/liminal-sites/liminal-sensorium-config.json';
  }

  function applyConfig(config) {
    if (!config || !config.layerConfig || !config.layerConfig.runtimeFlags || config.layerConfig.runtimeFlags.protectContent !== true) {
      throw new Error('Invalid sensorium config');
    }
    var reducedMotion = config.layerConfig.reducedMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    Object.keys(config.layerConfig.cssVariables || {}).forEach(function (name) {
      document.documentElement.style.setProperty(name, config.layerConfig.cssVariables[name]);
    });
    var layer = document.getElementById('liminal-sites-sensorium-layer');
    if (!layer) {
      layer = document.createElement('div');
      layer.id = 'liminal-sites-sensorium-layer';
      layer.setAttribute('aria-hidden', 'true');
      document.body.prepend(layer);
    }
    layer.style.pointerEvents = 'none';
    layer.dataset.motion = reducedMotion || config.layerConfig.motionIntensity <= 0.01 ? 'off' : 'on';
    document.documentElement.dataset.liminalSitesSensorium = config.configId;
    document.body.classList.add('liminal-sites-sensorium-active');
    receipt = {
      ready: true,
      source: 'liminal-sites-sensorium',
      configId: config.configId,
      siteId: config.siteId,
      confidence: config.signalVector && config.signalVector.confidence,
      protectedSurfaces: config.guardrails && config.guardrails.protectedSurfaces,
      reducedMotion: reducedMotion,
      error: null
    };
    window.__liminalSitesSensorium = receipt;
    window.dispatchEvent(new CustomEvent('liminal-sites-sensorium-ready', { detail: receipt }));
  }

  function boot() {
    var script = currentScript();
    fetch(configUrl(script), { credentials: 'same-origin' })
      .then(function (response) {
        if (!response.ok) throw new Error('Sensorium config failed with status ' + response.status);
        return response.json();
      })
      .then(applyConfig)
      .catch(markError);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
}());
