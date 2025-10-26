/* Optional Schema.org SoftwareApplication JSON-LD for Seev.
 * Enabled by default on all pages; harmless if ignored by crawlers.
 * If you need to disable, remove this file from mkdocs.yml extra_javascript.
 */
(function () {
  try {
    var data = {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "Seev",
      "applicationCategory": "DeveloperApplication",
      "operatingSystem": "Windows, macOS, Linux",
      "description": "Seev turns your real work—commits, PRs, and AI conversations—into a clean daily worklog.",
      "url": "https://bcosynot.github.io/seev/",
      "softwareVersion": "0.x",
      "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
      "publisher": {"@type": "Organization", "name": "Seev Project"}
    };
    var script = document.createElement('script');
    script.type = 'application/ld+json';
    script.textContent = JSON.stringify(data);
    document.head.appendChild(script);
  } catch(_) {}
})();
