"use client";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// Map our backend language keys to Prism language ids.
const LANG_MAP: Record<string, string> = {
  python: "python",
  javascript: "javascript",
  typescript: "typescript",
  tsx: "tsx",
  go: "go",
  java: "java",
  rust: "rust",
  c: "c",
  cpp: "cpp",
};

export function CodeBlock({
  code,
  language,
}: {
  code: string;
  language: string;
}) {
  return (
    <SyntaxHighlighter
      language={LANG_MAP[language] ?? "text"}
      style={oneDark}
      customStyle={{
        margin: 0,
        borderRadius: "0.5rem",
        fontSize: "0.8rem",
        background: "oklch(0.18 0 0)",
      }}
      wrapLongLines
    >
      {code}
    </SyntaxHighlighter>
  );
}
