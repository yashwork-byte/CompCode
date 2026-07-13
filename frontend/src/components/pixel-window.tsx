import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * A retro desktop "window": hard 2px border, offset drop shadow, and a
 * title bar with three square traffic-light controls (decorative).
 */
export function PixelWindow({
  title,
  actions,
  className,
  bodyClassName,
  children,
  ...props
}: React.ComponentProps<"section"> & {
  title: string;
  actions?: React.ReactNode;
  bodyClassName?: string;
}) {
  return (
    <section className={cn("pixel-window", className)} {...props}>
      <div className="title-bar">
        <span className="flex items-center gap-1.5" aria-hidden>
          <span className="dot" style={{ background: "var(--destructive)" }} />
          <span className="dot" style={{ background: "var(--chart-3)" }} />
          <span className="dot" style={{ background: "var(--primary)" }} />
        </span>
        <span className="mx-auto truncate px-2 text-foreground/80">{title}</span>
        <span className="ml-auto flex items-center">{actions}</span>
      </div>
      <div className={cn("p-4", bodyClassName)}>{children}</div>
    </section>
  );
}
