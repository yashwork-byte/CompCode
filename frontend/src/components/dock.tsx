"use client";

import { Database, Search, SquareTerminal, Cpu } from "lucide-react";
import type { LucideIcon } from "lucide-react";

const ITEMS: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "top", label: "Home", icon: Cpu },
  { id: "repo", label: "Repo", icon: Database },
  { id: "ask", label: "Ask", icon: Search },
  { id: "answer", label: "Output", icon: SquareTerminal },
];

export function Dock() {
  function go(id: string) {
    if (id === "top") {
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="fixed inset-x-0 bottom-4 z-50 flex justify-center px-4">
      <nav className="pixel-window flex items-end gap-2 !p-2">
        {ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => go(id)}
            title={label}
            className="group flex size-12 flex-col items-center justify-center gap-0.5 border-2 border-foreground/40 bg-secondary text-foreground/70 transition-all hover:-translate-y-1 hover:border-primary hover:text-primary"
          >
            <Icon className="size-5" strokeWidth={2.5} />
            <span className="font-pixel text-[6px] uppercase leading-none">{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
