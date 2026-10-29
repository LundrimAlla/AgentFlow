import LiveChat from "./live-chat";

export default function LivePage() {
  return <LiveChat siteKey={process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? ""}
    apiUrl={process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"} />;
}
