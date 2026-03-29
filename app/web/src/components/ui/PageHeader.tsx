import { cn } from "@/lib/cn";

export function PageHeader({
  eyebrow = "Mission workspace",
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel-surface px-6 py-6", className)}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="section-kicker">{eyebrow}</p>
          <h1 className="mt-2 text-[30px] font-semibold leading-tight text-white">{title}</h1>
          <p className="mt-3 text-sm leading-7 text-muted">{description}</p>
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-3">{actions}</div>}
      </div>
    </section>
  );
}
