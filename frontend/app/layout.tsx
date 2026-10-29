import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentFlow | AI workflows, made visible",
  description: "A portfolio project exploring grounded AI workflows using synthetic business data.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header">
      <Link className="brand" href="/"><span className="brand-mark" aria-hidden="true">aƒ</span> AgentFlow</Link>
      <nav aria-label="Main navigation"><Link href="/architecture">Architecture</Link><Link href="/demo">Workspace <span aria-hidden="true">↗</span></Link></nav>
    </header>
    <main id="main" tabIndex={-1}>{children}</main>
    <footer><span>AgentFlow / Engineering in the open</span><span>Synthetic data only · Demo + live preview</span></footer>
  </body></html>;
}
