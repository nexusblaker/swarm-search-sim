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
      className="inline-flex items-center gap-2 rounded-[18px] border border-border bg-surfaceAlt/75 px-3 py-2 text-sm text-white transition hover:border-accentStrong/40 hover:text-white"
    >
      <ExternalLink className="h-4 w-4" />
      {label}
    </a>
  );
}
