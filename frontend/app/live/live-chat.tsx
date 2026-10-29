"use client";

import Link from "next/link";
import Script from "next/script";
import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatRequest, ChatResponse, Citation, DocumentResponse, Message, SourceDocument } from "./api.generated";

type Widget = {
  render: (node: HTMLElement, options: {
    sitekey: string; action: string; size: "flexible" | "compact";
    callback: (token: string) => void;
    "expired-callback": () => void;
    "error-callback": (code: string) => void;
  }) => string;
  reset: (id: string) => void;
  remove: (id: string) => void;
};
declare global { interface Window { turnstile?: Widget } }

export default function LiveChat({ siteKey, apiUrl }: { siteKey: string; apiUrl: string }) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [invoiceResult, setInvoiceResult] = useState<DocumentResponse | null>(null);
  const [source, setSource] = useState<SourceDocument | null>(null);
  const [sourceStatus, setSourceStatus] = useState("");
  const sourceController = useRef<AbortController | null>(null);
  const sourcePanel = useRef<HTMLElement>(null);
  const citations = result?.citations ?? [];
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [verification, setVerification] = useState("Loading verification…");
  const container = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const pending = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => () => {
    controller.current?.abort();
    sourceController.current?.abort();
    if (widgetId.current !== null) window.turnstile?.remove(widgetId.current);
    widgetId.current = null;
  }, []);

  function clearSource() {
    sourceController.current?.abort();
    sourceController.current = null;
    setSource(null);
    setSourceStatus("");
  }

  async function viewSource(citation: Citation) {
    sourceController.current?.abort();
    const abort = new AbortController();
    sourceController.current = abort;
    setSource(null);
    setSourceStatus("Loading source…");
    sourcePanel.current?.focus();
    const timeout = window.setTimeout(() => abort.abort(), 7000);
    try {
      const response = await fetch(`${apiUrl}/api/sources/${encodeURIComponent(citation.corpus_id)}/${encodeURIComponent(citation.source_id)}`, { signal: abort.signal, credentials: "omit" });
      if (!response.ok) throw new Error("Unavailable");
      const document: SourceDocument = await response.json();
      if (document.corpus_id !== citation.corpus_id || document.source_id !== citation.source_id || typeof document.content !== "string") throw new Error("Invalid source");
      if (sourceController.current === abort) {
        setSource(document);
        setSourceStatus(`Source loaded. Quoted passage: lines ${citation.first_line}–${citation.last_line}.`);
      }
    } catch {
      if (sourceController.current === abort) setSourceStatus("Source unavailable. Your answer and excerpt remain above; try opening the source again.");
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function renderWidget() {
    if (!window.turnstile || !container.current || widgetId.current !== null) return;
    widgetId.current = window.turnstile.render(container.current, {
      sitekey: siteKey, action: "chat", size: "compact",
      callback: (value) => { setToken(value); setVerification("Verification complete."); },
      "expired-callback": () => { setToken(""); setVerification("Verification expired. Refresh it below."); },
      "error-callback": (code) => {
        setToken("");
        const reference = /^\d{6}$/.test(code) ? ` (${code})` : "";
        setVerification(`Verification unavailable${reference}. Try this page in Chrome or Edge, refresh, or use the offline demo.`);
      },
    });
  }

  function refreshVerification() {
    setToken("");
    setVerification("Waiting for verification…");
    if (widgetId.current !== null) window.turnstile?.reset(widgetId.current);
    else renderWidget();
  }

  async function extractSample() {
    if (pending.current || !token) return;
    pending.current = true;
    setBusy(true);
    setError("");
    setResult(null);
    setInvoiceResult(null);
    clearSource();
    const abort = new AbortController();
    controller.current = abort;
    const timeout = window.setTimeout(() => abort.abort(), 70000);
    try {
      const response = await fetch(`${apiUrl}/api/demo/document`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_id: "invoice-001", turnstile_token: token }),
        signal: abort.signal, credentials: "omit", cache: "no-store",
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        const message = response.status === 429 ? "Live quota reached. Return later to extract the sample."
          : response.status === 403 ? "Complete a fresh verification before extracting the sample."
          : response.status === 504 ? "Sample extraction took too long. Try again later."
          : "Sample extraction could not be validated. Try again later.";
        const reference = typeof detail?.request_id === "string" && /^[a-f0-9-]{36}$/.test(detail.request_id)
          ? ` Reference: ${detail.request_id}` : "";
        throw new Error(message + reference);
      }
      const data: DocumentResponse = await response.json();
      if (data.mode !== "live" || data.sample_id !== "invoice-001" || !data.invoice || !Array.isArray(data.trace)) {
        throw new Error("The server returned an unexpected extraction result.");
      }
      setInvoiceResult(data);
    } catch (cause) {
      setError(cause instanceof Error && cause.name !== "TypeError" && cause.name !== "AbortError"
        ? cause.message : "Could not reach sample extraction in time. Try again later.");
    } finally {
      window.clearTimeout(timeout);
      pending.current = false;
      setBusy(false);
      refreshVerification();
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending.current || !token || !draft.trim()) return;
    const next: Message[] = [...messages, { role: "user", content: draft.trim() }];
    const payload: ChatRequest = { messages: next, turnstile_token: token };
    const body = JSON.stringify(payload);
    if (new TextEncoder().encode(body).length > 20000) {
      setError("This conversation is too long. Start a new conversation before sending.");
      return;
    }
    pending.current = true;
    setBusy(true);
    setError("");
    setResult(null);
    setInvoiceResult(null);
    clearSource();
    const abort = new AbortController();
    controller.current = abort;
    const timeout = window.setTimeout(() => abort.abort(), 70000);
    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body,
        signal: abort.signal, credentials: "omit", cache: "no-store",
      });
      if (!response.ok) {
        const descriptions: Record<number, string> = {
          403: "Verification failed. Complete a fresh check and send again.",
          404: "Live chat is disabled. The offline demo is still available.",
          413: "Conversation too large. Start a new conversation.",
          422: "The message format was rejected. Start a new conversation.",
          429: "The live quota has been reached. Try the offline demo or return later.",
          502: "Gemini could not produce a valid reply. Please try again later.",
          503: "Live chat protection is unavailable. Please try again later.",
          504: "Live chat took too long. Please try again later.",
        };
        const detail = await response.json().catch(() => null);
        const timeoutMessages: Record<string, string> = {
          provider_timeout: "Gemini took too long to reply. Your draft is preserved; try again later.",
          embedding_timeout: "Document search took too long. Your draft is preserved; try again later.",
          request_timeout: "The workflow reached its time limit. Your draft is preserved; try again later.",
        };
        const message = (response.status === 504 && typeof detail?.error === "string"
          ? timeoutMessages[detail.error] : undefined)
          ?? descriptions[response.status] ?? "Live chat is unavailable. Try again later.";
        const reference = typeof detail?.request_id === "string" && /^[a-f0-9-]{36}$/.test(detail.request_id)
          ? ` Reference: ${detail.request_id}` : "";
        throw new Error(message + reference);
      }
      const data: ChatResponse = await response.json();
      if (data.mode !== "live" || typeof data.answer !== "string" || !Array.isArray(data.trace)) {
        throw new Error("The server returned an unexpected reply.");
      }
      setMessages([...next, { role: "assistant", content: data.answer }]);
      setResult(data);
      setDraft("");
    } catch (cause) {
      setError(cause instanceof Error && cause.name !== "TypeError" && cause.name !== "AbortError"
        ? cause.message : "Could not reach live chat in time. Your draft is preserved; try again later.");
    } finally {
      window.clearTimeout(timeout);
      pending.current = false;
      setBusy(false);
      refreshVerification();
    }
  }

  return <section className="workspace live-workspace">
    <div className="workspace-heading"><div><p className="eyebrow">EXPLORE / LIVE WORKSPACE</p>
      <h1>A real request.<br /><span>A visible workflow.</span></h1></div>
      <span className="demo-badge">LIVE AI · LIMITED PREVIEW</span></div>
    <p className="workspace-intro">Ask about fictional Alpine Components and inspect the source passages behind its answers, or draft a business request. Document creation is not available. No order or message is sent.</p>
    <p className="privacy-note">Use synthetic information only. Messages go to Google Gemini; verification uses Cloudflare. Google’s free tier may use submitted content to improve its products. Conversation history stays in this page’s memory and is sent with each question.</p>
    <p><Link className="text-link" href="/demo">Open the offline demo →</Link></p>
    <div className="workspace-grid">
      <section className="panel" aria-labelledby="live-conversation"><h2 id="live-conversation">Conversation</h2>
        {messages.length === 0 && <p className="workspace-intro">Try: “What products does Alpine Components offer?” or “Is there a published price list?”</p>}
        <div aria-live="polite" aria-relevant="additions" className="live-messages">{messages.map((message, index) => <div key={index} className={`message ${message.role === "user" ? "user-message" : "answer-message"}`}>
          <span className="message-author">{message.role === "user" ? "YOU" : "AGENTFLOW · LIVE"}</span><p>{message.content}</p>
        </div>)}</div>
        {result && citations.length > 0 && <section className="citations" aria-label="Sources for the latest answer">
          <h3>Sources for the latest answer</h3>
          <p>Passages retrieved from fictional company documents. Answers quote verified source text.</p>
          {citations.map((citation, index) => <div className="citation" key={`${citation.chunk_id}-${index}`}>
            <button type="button" aria-controls="live-source" onClick={() => viewSource(citation)}>[{index + 1}] {citation.title} · lines {citation.first_line}–{citation.last_line} ↗</button>
            <blockquote>{citation.excerpt}</blockquote>
          </div>)}
        </section>}
        <form onSubmit={submit}>
          <label htmlFor="live-question">Your message</label>
          <textarea ref={input} id="live-question" value={draft} onChange={(event) => setDraft(event.target.value)}
            maxLength={2000} rows={4} disabled={busy || messages.length >= 20} aria-describedby="message-limit" />
          <p id="message-limit" className="privacy-note">{draft.length}/2,000 characters · {messages.length / 2}/10 turns</p>
          <p className="privacy-note">Optional draft field: add a separate line such as “customer type: B2B”. Otherwise customer type stays unspecified.</p>
          {siteKey ? <>
            <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
              onReady={renderWidget} onError={() => setVerification("Verification could not load. Reload the page or use the offline demo.")} />
            <div ref={container} className="challenge-container" />
            <p role="status" className="run-status">{verification}</p>
            <button type="button" className="reset-button" disabled={busy} onClick={refreshVerification}>Refresh verification</button>
          </> : <p role="alert">Live verification is not configured. Use the offline demo.</p>}
          <div className="demo-controls">
            <button className="button primary" type="submit" disabled={busy || !token || !draft.trim() || messages.length >= 20}>{busy ? "Running workflow…" : "Send message →"}</button>
            <button className="reset-button" type="button" disabled={busy} onClick={() => {
              setMessages([]); setResult(null); setInvoiceResult(null); clearSource(); setError(""); setDraft(""); refreshVerification(); input.current?.focus();
            }}>New conversation</button>
          </div>
          {messages.length >= 20 && <p role="status">Ten turns complete. Start a new conversation to continue.</p>}
          {error && <p className="live-error" role="alert">{error}</p>}
          <p role="status" className="run-status">{busy ? "Verifying admission and running the workflow…" : invoiceResult ? "Sample extracted and all fields matched the fixture." : result ? "Live reply received." : "No request is running."}</p>
        </form>
        <section aria-labelledby="sample-invoice-title">
          <h3 id="sample-invoice-title">Extract a sample invoice</h3>
          <p>Read a fixed fictional text invoice with Gemini. This extracts existing fields; it creates no invoice or payment. The sample contains 12 brackets and 5 mounting plates, totaling €357.00 with tax. These are test prices.</p>
          <p className="privacy-note">Uses the verification above and the shared live quota. Your chat messages are not sent with this extraction.</p>
          <button type="button" className="button primary" disabled={busy || !token} onClick={extractSample}>Extract sample invoice →</button>
          {invoiceResult && <section aria-label="Validated invoice fields">
            <h3>Validated extraction · {invoiceResult.invoice.invoice_number}</h3>
            <p>{invoiceResult.invoice.supplier} → {invoiceResult.invoice.customer}</p>
            <p>Date: {invoiceResult.invoice.invoice_date} · Currency: {invoiceResult.invoice.currency}</p>
            <ul>{invoiceResult.invoice.items.map((item, index) => <li key={index}>{item.quantity} × {item.description} · €{(item.unit_price_cents / 100).toFixed(2)} each · €{(item.total_cents / 100).toFixed(2)}</li>)}</ul>
            <p>Subtotal: €{(invoiceResult.invoice.subtotal_cents / 100).toFixed(2)} · Tax: €{(invoiceResult.invoice.tax_cents / 100).toFixed(2)} · Total: €{(invoiceResult.invoice.total_cents / 100).toFixed(2)}</p>
            <p className="privacy-note">Every field matched this sample’s reviewed fixture. This does not establish accuracy for other documents.</p>
          </section>}
        </section>
      </section>
      <aside className="panel trace-panel" aria-labelledby="live-trace"><h2 id="live-trace">Latest workflow</h2>
        <p className="trace-disclaimer">Actual server stages and elapsed times. Safety means input validation and admission checks; it is not a guarantee against prompt injection. Lead extraction shares the router call. Skipped stages did not run.</p>
        {invoiceResult ? <>
          <ol className="trace-list">{invoiceResult.trace.map((step, index) => <li key={step.agent}><span className="trace-number">{index + 1}</span><div><h3>{step.agent}</h3><p>{step.status} · {step.duration_ms} ms</p></div></li>)}</ol>
          <p className="privacy-note">Request ID: {invoiceResult.request_id}. No document or payment created.</p>
        </> : result ? <>
          <ol className="trace-list">{result.trace.map((step, index) => <li key={step.agent}><span className="trace-number">{index + 1}</span><div><h3>{step.agent}</h3><p>{step.status} · {step.duration_ms} ms</p></div></li>)}</ol>
          {result.lead && <section className="lead-summary"><h3>Draft request</h3><dl>{Object.entries(result.lead).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value ?? "Not specified"}</dd></div>)}</dl><p>Model extraction can be wrong. Check these details; nothing is submitted.</p></section>}
          <p className="privacy-note">{citations.length ? `${citations.length} verified source passages cited.` : "No supporting source passages cited."} Request ID: {result.request_id}</p>
        </> : <p className="workspace-intro">Send a message to inspect its workflow.</p>}
      </aside>
    </div>
    <section ref={sourcePanel} tabIndex={-1} id="live-source" className="source-document panel" aria-labelledby="live-source-title">
      <h2 id="live-source-title">Source document{source ? ` / ${source.title}` : ""}</h2>
      <p role="status">{sourceStatus || "Select a citation to inspect the full source snapshot."}</p>
      {source && <><p className="privacy-note">Fictional company · version {source.corpus_id.slice(0, 12)}</p><pre>{source.content}</pre></>}
    </section>
  </section>;
}
