import { cn } from "@/lib/cn";

export function Panel({
  eyebrow,
  title,
  description,
  actions,
  footer,
  children,
  className,
}: {
  eyebrow?: string;
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("panel-surface p-6 md:p-7", className)}>
      {(eyebrow || title || description || actions) && (
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            {eyebrow && <p className="section-kicker">{eyebrow}</p>}
            {title && <h3 className="mt-2 text-[22px] font-semibold leading-tight text-white">{title}</h3>}
            {description && <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
      {footer && <div className="mt-7 border-t border-border/70 pt-5">{footer}</div>}
    </section>
  );
}
