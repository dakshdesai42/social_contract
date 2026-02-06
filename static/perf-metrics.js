(function () {
    'use strict';

    if (!('performance' in window) || !('PerformanceObserver' in window)) {
        return;
    }

    var sent = {};
    var clsValue = 0;
    var inpValue = null;
    var lcpValue = null;
    var fcpValue = null;

    function ratingFor(name, value) {
        if (value == null || Number.isNaN(value)) return 'unknown';
        if (name === 'LCP') return value <= 2500 ? 'good' : (value <= 4000 ? 'needs-improvement' : 'poor');
        if (name === 'INP') return value <= 200 ? 'good' : (value <= 500 ? 'needs-improvement' : 'poor');
        if (name === 'CLS') return value <= 0.1 ? 'good' : (value <= 0.25 ? 'needs-improvement' : 'poor');
        if (name === 'FCP') return value <= 1800 ? 'good' : (value <= 3000 ? 'needs-improvement' : 'poor');
        if (name === 'TTFB') return value <= 800 ? 'good' : (value <= 1800 ? 'needs-improvement' : 'poor');
        return 'unknown';
    }

    function sendMetric(name, value) {
        if (value == null || sent[name]) return;
        sent[name] = true;

        var payload = JSON.stringify({
            name: name,
            value: Number(value.toFixed ? value.toFixed(2) : value),
            rating: ratingFor(name, value),
            path: location.pathname
        });

        if (navigator.sendBeacon) {
            var blob = new Blob([payload], { type: 'application/json' });
            navigator.sendBeacon('/api/analytics/web-vitals', blob);
            return;
        }

        fetch('/api/analytics/web-vitals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: payload,
            keepalive: true,
            credentials: 'same-origin'
        }).catch(function () {});
    }

    try {
        var nav = performance.getEntriesByType('navigation');
        if (nav && nav[0] && nav[0].responseStart != null) {
            sendMetric('TTFB', nav[0].responseStart);
        }
    } catch (e) {}

    try {
        var fcpObserver = new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (entry) {
                if (entry.name === 'first-contentful-paint' && fcpValue == null) {
                    fcpValue = entry.startTime;
                    sendMetric('FCP', fcpValue);
                }
            });
        });
        fcpObserver.observe({ type: 'paint', buffered: true });
    } catch (e) {}

    try {
        var lcpObserver = new PerformanceObserver(function (list) {
            var entries = list.getEntries();
            var lastEntry = entries[entries.length - 1];
            if (lastEntry) lcpValue = lastEntry.startTime;
        });
        lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
    } catch (e) {}

    try {
        var clsObserver = new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (entry) {
                if (!entry.hadRecentInput) clsValue += entry.value;
            });
        });
        clsObserver.observe({ type: 'layout-shift', buffered: true });
    } catch (e) {}

    try {
        var inpObserver = new PerformanceObserver(function (list) {
            list.getEntries().forEach(function (entry) {
                var duration = entry.duration || 0;
                if (inpValue == null || duration > inpValue) inpValue = duration;
            });
        });
        inpObserver.observe({ type: 'event', buffered: true, durationThreshold: 40 });
    } catch (e) {}

    function flushVitals() {
        sendMetric('LCP', lcpValue);
        sendMetric('CLS', clsValue);
        sendMetric('INP', inpValue);
    }

    addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden') flushVitals();
    }, { capture: true });

    addEventListener('pagehide', flushVitals, { capture: true });
})();
