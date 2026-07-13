// Renders a unified diff with retro terminal colors.
export function DiffView({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <pre className="max-h-96 overflow-auto border-2 border-border bg-black/40 p-3 font-mono text-xs leading-relaxed">
      {lines.map((line, i) => {
        const added = line.startsWith("+") && !line.startsWith("+++");
        const removed = line.startsWith("-") && !line.startsWith("---");
        const hunk = line.startsWith("@@");
        const cls = added
          ? "text-primary bg-primary/10"
          : removed
            ? "text-destructive bg-destructive/10"
            : hunk
              ? "text-sky-400"
              : "text-muted-foreground";
        return (
          <div key={i} className={cls}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
