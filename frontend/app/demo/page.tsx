import { readFile } from "node:fs/promises";
import path from "node:path";
import scenarios from "../../../demo-data/scenarios.json";
import Workspace from "./workspace";
import InvoiceDemo from "./invoice-demo";
import invoice from "../../../backend/app/samples/invoice-001.expected.json";
import type { Invoice } from "../live/api.generated";

export const dynamic = "force-static";

export default async function Demo() {
  const ids = ["company", "products", "services", "pricing", "faq", "policies"];
  const sources = Object.fromEntries(await Promise.all(ids.map(async (id) => [
    id, await readFile(path.join(process.cwd(), "../demo-data/company", `${id}.md`), "utf8"),
  ])));
  const invoiceSource = await readFile(path.join(process.cwd(), "../backend/app/samples/invoice-001.txt"), "utf8");
  return <><Workspace scenarios={scenarios} sources={sources} />
    <div className="workspace"><InvoiceDemo source={invoiceSource} invoice={{ ...invoice, currency: "EUR" } satisfies Invoice} /></div>
  </>;
}
