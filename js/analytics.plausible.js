/* Optional Plausible analytics loader for MkDocs (opt‑in, disabled by default)
 * How to enable (build-time agnostic):
 *  1) In mkdocs.yml, add a page- or site-level meta tag under `extra.meta`:
 *       - name: "plausible:domain"
 *         content: "example.com"   // your docs domain
 *     (By default, this repo does NOT include it, so analytics is OFF.)
 *  2) Optionally add an SRI hash meta if you want Subresource Integrity:
 *       - name: "plausible:sri"
 *         content: "sha384-..."
 *  3) Rebuild the site. This script will inject the official Plausible script
 *     with `defer` and `crossorigin="anonymous"` only when the meta is present.
 *
 * Notes
 * - No PII is collected by Plausible. See https://plausible.io/data-policy
 * - SRI hashes change when Plausible updates their script. If you set SRI,
 *   be prepared to update the hash when upgrading. Leaving it unset skips SRI.
 */
(function () {
  try {
    var metaDomain = document.querySelector('meta[name="plausible:domain"]');
    if (!metaDomain || !metaDomain.content) {
      return; // analytics remains disabled by default
    }
    var domain = metaDomain.content.trim();
    if (!domain) return;

    var sriMeta = document.querySelector('meta[name="plausible:sri"]');
    var script = document.createElement('script');
    script.setAttribute('defer', '');
    script.setAttribute('data-domain', domain);
    script.setAttribute('src', 'https://plausible.io/js/script.js');
    script.setAttribute('crossorigin', 'anonymous');
    if (sriMeta && sriMeta.content) {
      script.setAttribute('integrity', sriMeta.content.trim());
    }
    document.head.appendChild(script);
  } catch (_) {
    // fail closed: do nothing
  }
})();
