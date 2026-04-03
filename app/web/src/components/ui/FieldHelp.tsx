export function FieldHelp({ text }: { text: string }) {
  return (
    <button
      type="button"
      className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border/80 bg-surfaceAlt/70 text-[11px] font-semibold text-muted transition hover:border-accentStrong/40 hover:text-white"
      title={text}
      aria-label={text}
    >
      ?
    </button>
  );
}
