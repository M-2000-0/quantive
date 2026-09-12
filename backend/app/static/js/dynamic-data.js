(function () {
  // Keep static pages usable when external analytics endpoints are absent.
  try {
    var originalFetch = window.fetch;
    window.fetch = function () {
      var url = (arguments[0] && typeof arguments[0] === 'string') ? arguments[0] : '';
      if (/^\/api\/metrics\/track/i.test(url)) {
        return Promise.resolve(new Response('{}', { status: 204 }));
      }
      return originalFetch.apply(this, arguments);
    };
  } catch (e) {}
})();
