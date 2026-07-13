"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import {
  FolderGit2,
  Loader2,
  Search,
  Database,
  FileCode2,
  Route,
  Check,
  X,
  GitPullRequest,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { CodeBlock } from "@/components/code-block";
import { PixelWindow } from "@/components/pixel-window";
import { DiffView } from "@/components/diff-view";
import {
  indexRepo,
  queryRepoStream,
  resumeStream,
  newThreadId,
  type IndexResult,
  type QueryResult,
  type EditPlan,
  type StreamHandlers,
} from "@/lib/api";

export default function Home() {
  const [repo, setRepo] = useState("");
  const [token, setToken] = useState("");
  const [query, setQuery] = useState("");

  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState<IndexResult | null>(null);

  const [querying, setQuerying] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);

  // Edit workflow review gate.
  const threadRef = useRef<string>("");
  const [review, setReview] = useState<{ threadId: string; plan: EditPlan } | null>(null);
  const [feedback, setFeedback] = useState("");
  const [resuming, setResuming] = useState(false);

  async function handleIndex() {
    if (!repo.trim()) {
      toast.error("Enter a repository path or GitHub URL");
      return;
    }
    setIndexing(true);
    setIndexResult(null);
    try {
      const res = await indexRepo(repo.trim(), token.trim());
      setIndexResult(res);
      toast.success(
        `Indexed ${res.num_functions} functions (${res.languages.join(", ") || "—"})`,
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Indexing failed");
    } finally {
      setIndexing(false);
    }
  }

  // Shared handlers for both the initial query and any resume.
  function handlers(): StreamHandlers {
    return {
      onMeta: (meta) => {
        setResult({ answer: "", route: meta.route, functions: meta.functions });
        setQuerying(false);
      },
      onToken: (text) => {
        setResult((prev) => (prev ? { ...prev, answer: prev.answer + text } : prev));
      },
      onInterrupt: (data) => {
        // Edit paused for review — show the diff.
        setReview({ threadId: data.thread_id, plan: data.plan });
        setStreaming(false);
        setResuming(false);
      },
      onDone: () => {
        setStreaming(false);
        setResuming(false);
      },
      onError: (message) => {
        toast.error(message);
        setQuerying(false);
        setStreaming(false);
        setResuming(false);
      },
    };
  }

  async function handleQuery() {
    if (!query.trim()) {
      toast.error("Ask a question first");
      return;
    }
    if (!repo.trim()) {
      toast.error("Enter (and index) a repository first");
      return;
    }
    threadRef.current = newThreadId();
    setQuerying(true);
    setStreaming(true);
    setResult(null);
    setReview(null);
    await queryRepoStream(repo.trim(), query.trim(), token.trim(), threadRef.current, handlers());
  }

  async function handleApprove() {
    if (!review) return;
    setResuming(true);
    setStreaming(true);
    setReview(null);
    await resumeStream(review.threadId, "approve", undefined, handlers());
  }

  async function handleReject() {
    if (!review) return;
    const fb = feedback.trim();
    setResuming(true);
    setReview(null);
    setFeedback("");
    await resumeStream(review.threadId, "reject", fb, handlers());
  }

  const busy = querying || streaming || resuming;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">
      {/* Hero */}
      <header id="top" className="mb-8 scroll-mt-14">
        <h1 className="font-pixel text-2xl leading-tight text-primary sm:text-3xl">
          CodeComp
        </h1>
        <p className="mt-3 font-terminal text-xl leading-snug text-foreground/80">
          Ask questions about a codebase, or ask it to make a change — reviewed,
          verified, and re-indexed. Python, JS/TS, Go, Java, Rust and C/C++.
        </p>
      </header>

      {/* Repository */}
      <PixelWindow
        id="repo"
        title="repo — finder"
        className="mb-6 scroll-mt-14"
        actions={
          indexResult && (
            <span className="hl !text-[8px]">{indexResult.num_functions} fns</span>
          )
        }
      >
        <div className="mb-4 flex items-center gap-2 font-pixel text-[10px] text-foreground/70">
          <Database className="size-4 text-primary" /> REPOSITORY
        </div>
        <p className="mb-4 font-terminal text-lg text-muted-foreground">
          A local path or a GitHub URL. Editing needs a local path; GitHub repos are
          read-only (QA).
        </p>

        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <FolderGit2 className="text-muted-foreground absolute left-3 top-1/2 size-4 -translate-y-1/2" />
            <Input
              className="pl-9"
              placeholder="https://github.com/user/repo  or  /path/to/repo"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              disabled={indexing}
            />
          </div>
          <Button onClick={handleIndex} disabled={indexing} className="sm:w-40">
            {indexing ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Indexing
              </>
            ) : (
              "Index"
            )}
          </Button>
        </div>

        <div className="mt-4 space-y-1.5">
          <Label
            htmlFor="token"
            className="font-pixel text-[8px] uppercase text-muted-foreground"
          >
            GitHub token — private repos only
          </Label>
          <Input
            id="token"
            type="password"
            placeholder="ghp_…"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            disabled={indexing}
          />
        </div>

        {indexResult && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              <FileCode2 className="size-3" />
              {indexResult.num_functions} functions
            </Badge>
            {indexResult.languages.map((l) => (
              <Badge key={l} variant="outline">
                {l}
              </Badge>
            ))}
          </div>
        )}
      </PixelWindow>

      {/* Ask */}
      <PixelWindow id="ask" title="ask — terminal" className="mb-6 scroll-mt-14">
        <div className="mb-4 flex items-center gap-2 font-pixel text-[10px] text-foreground/70">
          <Search className="size-4 text-primary" /> ASK
        </div>
        <Textarea
          placeholder="> how does indexing work?   ·   > add a mul() to calc.py"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") handleQuery();
          }}
          rows={3}
          disabled={busy}
        />
        <div className="mt-3 flex items-center justify-between">
          <span className="font-pixel text-[8px] uppercase text-muted-foreground">
            ⌘/Ctrl + ↵ to send
          </span>
          <Button onClick={handleQuery} disabled={busy}>
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Working
              </>
            ) : (
              "Ask"
            )}
          </Button>
        </div>
      </PixelWindow>

      {/* Loading skeleton (before the first meta) */}
      {querying && (
        <PixelWindow title="output — running" className="mb-6">
          <div className="space-y-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </PixelWindow>
      )}

      {/* Review gate (edit workflow paused for approval) */}
      {review && (
        <PixelWindow
          title="review — pull request"
          className="mb-6"
          actions={<span className="hl !text-[8px]">needs approval</span>}
        >
          <div className="mb-3 flex items-center gap-2 font-pixel text-[10px] text-foreground/70">
            <GitPullRequest className="size-4 text-primary" />
            <span className="font-mono text-sm normal-case">{review.plan.file}</span>
          </div>
          <p className="mb-3 font-terminal text-lg text-foreground/80">
            {review.plan.rationale}
          </p>
          <DiffView diff={review.plan.diff} />

          <div className="mt-4 space-y-2">
            <Label className="font-pixel text-[8px] uppercase text-muted-foreground">
              Feedback (optional — sent back to the agent on reject)
            </Label>
            <Textarea
              placeholder="e.g. use a list comprehension instead"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={2}
              disabled={resuming}
            />
          </div>

          <div className="mt-4 flex items-center gap-2">
            <Button onClick={handleApprove} disabled={resuming}>
              <Check className="size-4" /> Approve &amp; apply
            </Button>
            <Button variant="secondary" onClick={handleReject} disabled={resuming}>
              <X className="size-4" /> Reject &amp; revise
            </Button>
            {resuming && <Loader2 className="size-4 animate-spin text-primary" />}
          </div>
        </PixelWindow>
      )}

      {/* Answer */}
      {result?.answer && !querying && (
        <PixelWindow
          id="answer"
          title="output — answer"
          className="mb-6 scroll-mt-14"
          actions={
            <Badge variant={result.route === "edit" ? "destructive" : "secondary"}>
              <Route className="size-3" />
              {result.route}
            </Badge>
          }
        >
          <p
            className={
              "font-terminal text-xl leading-relaxed whitespace-pre-wrap text-foreground/90" +
              (streaming ? " caret" : "")
            }
          >
            {result.answer}
          </p>
        </PixelWindow>
      )}

      {/* Relevant functions */}
      {result && result.functions.length > 0 && !querying && (
        <div className="scroll-mt-14">
          <div className="mb-3 flex items-center gap-2">
            <span className="hl">Relevant functions</span>
            <Badge variant="outline">{result.functions.length}</Badge>
          </div>
          <Accordion className="space-y-2">
            {result.functions.map((f, i) => (
              <AccordionItem
                key={`${f.file}:${f.function}:${i}`}
                value={`${i}`}
                className="pixel-window px-4"
              >
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex flex-1 items-center gap-2 text-left">
                    <FileCode2 className="size-4 text-primary" />
                    <span className="font-mono text-sm">{f.function}</span>
                    {f.language && <Badge variant="outline">{f.language}</Badge>}
                    <span className="text-muted-foreground ml-auto truncate pl-2 font-mono text-xs">
                      {f.file}
                    </span>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <CodeBlock code={f.code} language={f.language} />
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      )}
    </main>
  );
}
