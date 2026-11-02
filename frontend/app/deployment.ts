export const offlineExport = process.env.OFFLINE_EXPORT === "true";

// GitHub Pages cannot set custom response headers. Apply supported CSP directives
// through HTML; frame-ancestors is deliberately omitted because meta cannot enforce it.
export const offlineCsp = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'";
