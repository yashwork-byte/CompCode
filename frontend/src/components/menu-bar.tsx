"use client";

import { useEffect, useRef, useState } from "react";

import { emit } from "@/lib/bus";
import { HelpDialog } from "@/components/help-dialog";

type Item = { label: string; onSelect: () => void };

function scrollTo(id: string) {
  if (id === "top") {
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function focusQuery() {
  const el = document.getElementById("query-box") as HTMLTextAreaElement | null;
  scrollTo("ask");
  el?.focus();
}

function Dropdown({ label, items }: { label: string; items: Item[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className={`font-pixel text-[9px] transition-colors ${
          open ? "text-primary" : "text-foreground/60 hover:text-foreground"
        }`}
      >
        {label}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 min-w-48 border-2 border-foreground/60 bg-card py-1 shadow-[4px_4px_0_0_rgba(0,0,0,0.5)]">
          {items.map((it) => (
            <button
              key={it.label}
              onClick={() => {
                setOpen(false);
                it.onSelect();
              }}
              className="block w-full px-3 py-1.5 text-left font-terminal text-base text-foreground/80 hover:bg-primary hover:text-primary-foreground"
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function MenuBar() {
  const [clock, setClock] = useState("");
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    const tick = () =>
      setClock(
        new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      );
    tick();
    const id = setInterval(tick, 10_000);
    return () => clearInterval(id);
  }, []);

  const editItems: Item[] = [
    { label: "Focus query", onSelect: focusQuery },
    { label: "Clear query", onSelect: () => emit("clear-query") },
    { label: "New session", onSelect: () => emit("reset-session") },
  ];
  const viewItems: Item[] = [
    { label: "Top", onSelect: () => scrollTo("top") },
    { label: "Repository", onSelect: () => scrollTo("repo") },
    { label: "Ask", onSelect: () => scrollTo("ask") },
    { label: "Output", onSelect: () => scrollTo("answer") },
  ];

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50 flex h-9 items-center gap-4 border-b-2 border-foreground/60 bg-card/95 px-3 backdrop-blur">
        <span className="font-pixel text-[10px] text-primary">◆ CodeComp</span>
        <nav className="hidden items-center gap-4 sm:flex">
          <Dropdown label="Edit" items={editItems} />
          <Dropdown label="View" items={viewItems} />
          <button
            onClick={() => setHelpOpen(true)}
            className="font-pixel text-[9px] text-foreground/60 transition-colors hover:text-foreground"
          >
            Help
          </button>
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
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}
