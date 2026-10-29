"use client";

import { useRef, useState } from "react";
import type { Invoice } from "../live/api.generated";

export default function InvoiceDemo({ source, invoice }: { source: string; invoice: Invoice }) {
  const [shown, setShown] = useState(false);
  const showButton = useRef<HTMLButtonElement>(null);
  const euro = (cents: number) => `€${(cents / 100).toFixed(2)}`;
  return <section className="panel source-document" aria-labelledby="offline-invoice-title">
    <div className="panel-heading"><h2 id="offline-invoice-title">Sample invoice walkthrough</h2><span className="pill">DEMO MODE · OFFLINE</span></div>
    <p>Inspect the same fictional invoice used by live extraction. This shows a prepared fixture. No AI, backend, verification or payment runs.</p>
    <details><summary>Read the synthetic source invoice</summary><pre>{source}</pre></details>
    <div className="demo-controls">
      <button ref={showButton} className="button primary" onClick={() => setShown(true)}>Show prepared invoice fields</button>
      <button className="reset-button" disabled={!shown} onClick={() => { setShown(false); showButton.current?.focus(); }}>Reset invoice demo</button>
    </div>
    <p role="status">{shown ? "Prepared invoice fields and illustrative stages are shown below." : "Ready to show the bundled result."}</p>
    {shown && <div className="workspace-grid">
      <section aria-label="Prepared invoice fields">
        <h3>{invoice.invoice_number} · Prepared result</h3>
        <dl>
          <dt>Supplier</dt><dd>{invoice.supplier}</dd>
          <dt>Customer</dt><dd>{invoice.customer}</dd>
          <dt>Invoice date</dt><dd>{invoice.invoice_date}</dd>
          <dt>Currency</dt><dd>{invoice.currency}</dd>
        </dl>
        <ul>{invoice.items.map((item, index) => <li key={index}>{item.quantity} × {item.description} · {euro(item.unit_price_cents)} each · {euro(item.total_cents)}</li>)}</ul>
        <p>Subtotal: {euro(invoice.subtotal_cents)} · Tax: {euro(invoice.tax_cents)} · Total: {euro(invoice.total_cents)}</p>
        <p>All amounts are fictional test data. This invoice is not payable and is not a company price list.</p>
      </section>
      <aside aria-label="Illustrative invoice workflow">
        <h3>Illustrative workflow</h3>
        <p>No agents ran. No timings are simulated.</p>
        <ol>
          <li>Select the allowlisted synthetic invoice.</li>
          <li>Extract typed fields, using integer cents for amounts.</li>
          <li>Compare every field with the reviewed sample fixture.</li>
        </ol>
      </aside>
    </div>}
  </section>;
}
