import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const base = new URL("../../demo-data/", import.meta.url);
const scenarios = JSON.parse(readFileSync(new URL("scenarios.json", base), "utf8"));
const sourceIds = ["company", "products", "services", "pricing", "faq", "policies"];

test("all six documents explicitly identify the fictional context", () => {
  for (const id of sourceIds) {
    assert.match(readFileSync(new URL(`company/${id}.md`, base), "utf8"), /fictional/i);
  }
});

test("scenarios have distinct IDs and complete bounded walkthroughs", () => {
  assert.equal(scenarios.length, 3);
  assert.equal(new Set(scenarios.map((s) => s.id)).size, 3);
  for (const scenario of scenarios) {
    for (const field of ["id", "title", "description", "question", "answer"]) {
      assert.equal(typeof scenario[field], "string");
      assert.ok(scenario[field].trim().length > 0);
    }
    assert.ok(scenario.question.length <= 2000);
    assert.ok(scenario.answer.length <= 8000);
    assert.ok(scenario.citations.length > 0);
    assert.equal(scenario.trace[0].agent, "Safety");
    assert.equal(scenario.trace.at(-1).agent, "Validation");
    assert.ok(scenario.trace.every((step) => step.detail && !("duration_ms" in step)));
  }
});

test("every citation is a verbatim excerpt from an allowlisted document", () => {
  for (const scenario of scenarios) {
    for (const citation of scenario.citations) {
      assert.ok(sourceIds.includes(citation.source));
      assert.ok(citation.excerpt.length > 30);
      const document = readFileSync(new URL(`company/${citation.source}.md`, base), "utf8");
      assert.ok(document.includes(citation.excerpt), `Broken citation in ${scenario.id}`);
    }
  }
});

test("quote and delivery examples preserve unknowns and avoid false commitments", () => {
  const quote = scenarios.find((s) => s.id === "quote-request");
  assert.equal(quote.lead.quantity, 200);
  assert.equal(quote.lead.urgency, null);
  assert.match(quote.question, /200 aluminium brackets/);
  assert.match(quote.answer, /Nothing has been submitted/);
  assert.match(scenarios.find((s) => s.id === "delivery-policy").answer, /cannot guarantee/);
});
