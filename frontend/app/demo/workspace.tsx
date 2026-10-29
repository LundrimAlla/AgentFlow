"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import type fixture from "../../../demo-data/scenarios.json";

type Props = { scenarios: typeof fixture; sources: Record<string, string> };

export default function Workspace({ scenarios, sources }: Props) {
  const [selected, setSelected] = useState(scenarios[0]?.id ?? "");
  const [completed, setCompleted] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const evidence = useRef<HTMLElement>(null);
  const runButton = useRef<HTMLButtonElement>(null);
  const scenario = scenarios.find((item) => item.id === selected);
  const result = completed === selected ? scenario : undefined;

  function select(id: string) {
    setSelected(id);
    setCompleted(null);
    setSource(null);
  }

  function openSource(id: string) {
    setSource(id);
    evidence.current?.focus();
  }

  return <section className="workspace">
    <div className="workspace-heading"><div><p className="eyebrow">EXPLORE / AGENT WORKSPACE</p><h1>A question. A workflow.<br /><span>Evidence you can inspect.</span></h1></div><span className="demo-badge">DEMO MODE · OFFLINE</span></div>
    <p className="workspace-intro">Choose a synthetic scenario to explore a prepared answer. No live AI runs, no request is submitted, and traces are illustrative.</p>
    <p><Link className="text-link" href="/live">Try the protected live preview →</Link></p>
    <p className="privacy-note">Do not submit personal, confidential, or sensitive information. This demo accepts preset scenarios only.</p>
    <fieldset className="scenario-picker"><legend>1. Choose a scenario</legend><div className="scenario-grid">{scenarios.map((item, index) => <label key={item.id} className={`scenario-option ${selected === item.id ? "selected" : ""}`}>
      <input type="radio" name="scenario" value={item.id} checked={selected === item.id} onChange={() => select(item.id)} />
      <span><span className="step-number">0{index + 1}</span><strong>{item.title}</strong><span className="scenario-description">{item.description}</span></span>
    </label>)}</div></fieldset>
    <div className="workspace-grid">
      <section className="conversation panel" aria-labelledby="conversation-title">
        <div className="panel-heading"><h2 id="conversation-title">Conversation</h2><span className="pill">Synthetic example</span></div>
        {scenario ? <>
          <div className="message user-message"><span className="message-author">PRESET QUESTION</span><p>{scenario.question}</p></div>
          <div className="demo-controls"><button ref={runButton} className="button primary" onClick={() => { setCompleted(selected); setSource(null); }}>Run demo scenario <span aria-hidden="true">→</span></button><button className="reset-button" disabled={!result} onClick={() => { setCompleted(null); setSource(null); runButton.current?.focus(); }}>Reset scenario</button></div>
          <div role="status" className="run-status">{result ? "Demo complete. Prepared answer and illustrative trace are available below." : "Ready. Run this scenario to view its prepared result."}</div>
          {result && <>
            <div className="message answer-message"><span className="message-author">AGENTFLOW · PREPARED ANSWER</span><p>{result.answer}</p></div>
            {result.lead && <section className="lead-summary" aria-label="Prepared quote request"><h3>Prepared request</h3><dl>{Object.entries(result.lead).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{value ?? "Not specified"}</dd></div>)}</dl><p>Illustrative extraction. Nothing has been sent.</p></section>}
            <section className="citations" aria-label="Supporting evidence"><h3>2. Inspect supporting evidence</h3><p>These excerpts were selected when the scenario was authored, not retrieved live.</p>{result.citations.map((citation, index) => <div className="citation" key={`${citation.source}-${index}`}><button aria-controls="source-document" onClick={() => openSource(citation.source)}>[{index + 1}] {citation.source} <span aria-hidden="true">↗</span></button><blockquote>{citation.excerpt}</blockquote></div>)}</section>
          </>}
        </> : <p role="alert">No demo scenario is available. Reload the page to try again.</p>}
      </section>
      <aside className="trace-panel panel" aria-labelledby="trace-title"><div className="panel-heading"><h2 id="trace-title">Agent workflow</h2><span className="pill">Illustrative</span></div><p className="trace-disclaimer">A walkthrough of the planned stages. No agents executed, and no timings are simulated.</p>
        {result ? <><p className="intent-label">Intent: {result.intent}</p><ol className="trace-list">{result.trace.map((step, index) => <li key={step.agent}><span className="trace-number" aria-hidden="true">{index + 1}</span><div><h3>{step.agent}</h3><p>{step.detail}</p></div></li>)}</ol></> : <div className="trace-empty"><span aria-hidden="true">↳</span><p>Run a scenario to explore its workflow.</p></div>}
      </aside>
    </div>
    <section id="source-document" className="source-document panel" ref={evidence} tabIndex={-1} aria-labelledby="source-title"><div className="panel-heading"><h2 id="source-title">Source document{source ? ` / ${source}` : ""}</h2><span className="pill">Fictional company · v1</span></div>{source ? sources[source] ? <pre>{sources[source]}</pre> : <p role="alert">This source is unavailable in the bundled knowledge base. Choose another citation.</p> : <p>Select a source above to read the full document here.</p>}</section>
  </section>;
}
