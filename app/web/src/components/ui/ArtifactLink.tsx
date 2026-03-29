import { ExternalLink } from "lucide-react";

export function ArtifactLink({
  href,
  label,
}: {
  href: string;
  label: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-2 rounded-xl border border-border bg-surfaceAlt px-3 py-2 text-sm text-white transition hover:border-accent/40 hover:text-accent"
    >
      <ExternalLink className="h-4 w-4" />
      {label}
    </a>
  );
}
