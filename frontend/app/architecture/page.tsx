const layers = [
  ["Interface", "Next.js · React · TypeScript", "Renders answers, citations, and safe execution metadata. Bundled scenarios work without the API."],
  ["Application", "FastAPI · Pydantic", "Validates requests and coordinates bounded live intent routing, draft lead extraction, and responses."],
  ["Knowledge", "PostgreSQL · pgvector", "Versioned document snapshots and embeddings support live retrieval. Citations open the exact source version used for an answer."],
  ["Admission controls", "Turnstile · Upstash Redis", "Server-side bot verification protects public workflows. Every model call reserves its usage budget atomically."],
];

export default function Architecture() {
  return <section className="content-page"><p className="eyebrow">SYSTEM DESIGN</p><h1>Small pieces.<br />Explicit boundaries.</h1><p className="intro">One frontend, one modular backend, and a versioned knowledge base. Live workflows expose operational steps without revealing private model reasoning.</p>
    <div className="architecture-list">{layers.map(([title, tech, description], i) => <article key={title}><span className="step-number">0{i + 1}</span><div><h2>{title}</h2><p className="tech">{tech}</p><p>{description}</p></div></article>)}</div>
    <p className="notice">Current implementation: offline scenarios and an invoice walkthrough, protected live chat, fictional draft requests, source-grounded retrieval and sample invoice extraction. Operational metrics have seven-day retention with periodic cleanup. Document creation and arbitrary uploads are unavailable.</p>
  </section>;
}
