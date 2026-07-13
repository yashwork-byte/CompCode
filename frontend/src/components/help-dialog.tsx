"use client";

import { useEffect } from "react";
import { X } from "lucide-react";
import { PixelWindow } from "@/components/pixel-window";

const SHORTCUTS: [string, string][] = [
  ["Edit → Focus / Clear query", "Jump to or empty the ask box."],
  ["Edit → New session", "Clear the current question and output."],
  ["View", "Scroll to Top, Repository, Ask, or Output."],
  ["⌘/Ctrl + ↵", "Send your question from the ask box."],
];

const STEPS: [string, string][] = [
  ["1. Point at a repo", "Paste a GitHub URL or a local path, then click Index."],
  ["2. Ask", "Ask a question about the code, or request an edit (e.g. “add a mul() to calc.py”)."],
  ["3. Review edits", "Edits are local-only. You get a diff to Approve or Reject with feedback."],
  ["4. Verify", "Approved edits are compiled/linted (and tested if enabled), then re-indexed."],
];

export function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Help"
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <PixelWindow
        title="help — read me"
        className="relative z-10 max-h-[85vh] w-full max-w-lg overflow-auto"
        actions={
          <button
            onClick={onClose}
            aria-label="Close help"
            className="flex size-4 items-center justify-center text-foreground/70 hover:text-primary"
          >
            <X className="size-3.5" />
          </button>
        }
      >
        <p className="mb-4 font-terminal text-lg leading-snug text-foreground/80">
          CodeComp answers questions about a codebase and can make reviewed,
          verified edits to local repos.
        </p>

        <div className="mb-4 space-y-2">
          {STEPS.map(([title, body]) => (
            <div key={title} className="border-2 border-border bg-black/20 p-2.5">
              <div className="font-pixel text-[9px] text-primary">{title}</div>
              <div className="mt-1 font-terminal text-base leading-snug text-foreground/75">
                {body}
              </div>
            </div>
          ))}
        </div>

        <div className="mb-2 font-pixel text-[9px] uppercase text-muted-foreground">
          Menus & shortcuts
        </div>
        <dl className="space-y-1.5">
          {SHORTCUTS.map(([key, desc]) => (
            <div key={key} className="flex gap-3">
              <dt className="w-40 shrink-0 font-mono text-xs text-foreground/70">{key}</dt>
              <dd className="font-terminal text-base leading-snug text-foreground/70">{desc}</dd>
            </div>
          ))}
        </dl>
      </PixelWindow>
    </div>
  );
}
