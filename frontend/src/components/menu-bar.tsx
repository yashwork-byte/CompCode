"use client";

import { useEffect, useState } from "react";

const MENUS = ["File", "Edit", "View", "Help"];

export function MenuBar() {
  const [clock, setClock] = useState("");

  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      );
    tick();
    const id = setInterval(tick, 10_000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-9 items-center gap-4 border-b-2 border-foreground/60 bg-card/95 px-3 backdrop-blur">
      <span className="font-pixel text-[10px] text-primary">◆ CodeComp</span>
      <nav className="hidden items-center gap-4 sm:flex">
        {MENUS.map((m) => (
          <span
            key={m}
            className="font-pixel text-[9px] text-foreground/60 transition-colors hover:text-foreground"
          >
            {m}
          </span>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-1.5 font-pixel text-[9px] text-foreground/60">
          <span
            className="inline-block size-2 bg-primary"
            style={{ boxShadow: "0 0 6px var(--primary)" }}
          />
          ONLINE
        </span>
        <span className="font-terminal text-lg leading-none text-foreground/80 tabular-nums">
          {clock || "--:--"}
        </span>
      </div>
    </header>
  );
}
