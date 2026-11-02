import { readFile } from "node:fs/promises";
import assert from "node:assert/strict";

for (const route of ["", "demo/", "architecture/", "live/"]) {
  const html = await readFile(`.next-demo/${route}index.html`, "utf8");
  assert.match(html, /Content-Security-Policy/);
  assert.match(html, /connect-src &#x27;self&#x27;|connect-src 'self'/);
  assert.match(html, /\/AgentFlow\/_next\//);
  assert.doesNotMatch(html, /http:\/\/(?:127\.0\.0\.1|localhost)/);
  assert.doesNotMatch(html, /challenges\.cloudflare\.com/);
  if (route === "live/") {
    assert.match(html, /Live AI is disabled/);
    assert.doesNotMatch(html, /<textarea|<form|<iframe/);
  }
}
console.log("Offline export verified: prefixed assets, CSP, no local API or verification widget.");
