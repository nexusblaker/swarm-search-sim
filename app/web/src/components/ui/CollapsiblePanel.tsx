import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/cn";

export function CollapsiblePanel({
  title,
  description,
  badge,
  defaultOpen = true,
  children,
  className,
  headerClassName,
}: {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
  headerClassName?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className={cn("panel-subtle overflow-hidden", className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-start justify-between gap-4 px-5 py-4 text-left transition duration-150 hover:bg-white/[0.03]",
          headerClassName,
        )}
        aria-expanded={open}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-white">{title}</h3>
            {badge}
          </div>
          {description && <p className="mt-1 text-sm leading-6 text-muted">{description}</p>}
        </div>
        <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border/75 bg-surfaceAlt/85 text-muted">
          <ChevronDown
            className={cn("h-4 w-4 transition duration-200", open && "rotate-180 text-white")}
          />
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/65 px-5 py-5">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
