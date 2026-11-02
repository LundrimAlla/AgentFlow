import Link from "next/link";
import { offlineExport } from "../deployment";

export default async function LivePage() {
  if (offlineExport) return <section className="content-page">
    <p className="eyebrow">PUBLIC PORTFOLIO DEMO</p><h1>Explore the offline workspace.</h1>
    <p className="intro">Live AI is disabled on this public site. Explore prepared scenarios, fictional sources, and an illustrative invoice walkthrough without submitting any data.</p>
    <Link className="button primary" href="/demo">Open demo workspace →</Link>
  </section>;
  const { default: LiveChat } = await import("./live-chat");
  return <LiveChat siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? ""}
    apiUrl={process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"} />;
}
