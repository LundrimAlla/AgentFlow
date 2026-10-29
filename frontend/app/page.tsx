import Link from "next/link";

const stages = [
  ["01", "Understand", "Validate the request and select a bounded workflow."],
  ["02", "Ground", "Retrieve relevant company knowledge with traceable sources."],
  ["03", "Respond", "Return a structured answer and a clear execution trace."],
];

export default function Home() {
  return <>
    <section className="hero">
      <div className="hero-copy"><p className="eyebrow"><span className="dot" /> A portfolio project in progress</p>
        <h1>Useful AI.<br /><span>Visible decisions.</span></h1>
        <p className="intro">From a business question to a grounded answer. Explore how focused agents, company knowledge, and careful validation fit together.</p>
        <div className="actions"><Link className="button primary" href="/demo">Open workspace <span aria-hidden="true">↗</span></Link><Link className="text-link" href="/architecture">Explore the architecture →</Link></div>
        <p className="small muted">Built with synthetic data. Explore the offline demo or the protected live preview.</p>
      </div>
      <div className="flow-card" aria-label="Planned agent workflow diagram">
        <div className="card-heading"><span>THE WORKFLOW</span><span className="pill">Design preview</span></div>
        <div className="question">“What can your company help us build?”</div>
        <div className="flow-line" />
        <div className="flow-node"><span className="node-icon">01</span><div><strong>Safety & routing</strong><p>Validate, then choose a path</p></div><span className="node-tag">CHECK</span></div>
        <div className="flow-line" />
        <div className="flow-node accent"><span className="node-icon">02</span><div><strong>Knowledge retrieval</strong><p>Find supporting evidence</p></div><span className="node-tag">RAG</span></div>
        <div className="flow-line" />
        <div className="flow-node"><span className="node-icon">03</span><div><strong>Response & validation</strong><p>Answer with sources</p></div><span className="node-tag">OUTPUT</span></div>
        <p className="diagram-note">An architecture illustration, not a live execution.</p>
      </div>
    </section>
    <section className="principles" aria-label="Engineering principles">{stages.map(([number, title, text]) => <article key={number}><span className="step-number">/{number}</span><h2>{title}</h2><p>{text}</p></article>)}</section>
  </>;
}
