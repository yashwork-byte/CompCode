import json

from ingestion.index import index_repo
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from agents.debugger import debugger_agent
from router import route_query

from eval.judge import judge_explanation, judge_debugger
from eval.metrics import retrieval_recall


def run_eval(repo_path):
    index_repo(repo_path)

    tests = json.load(open("eval/test_cases.json"))

    for t in tests:
        q = t["query"]
        typ = t.get("type", "explanation")

        print("\n---")
        print(q)

        route = route_query(q)
        print("route:", route)

        if typ == "explanation":
            results, expanded = search_code(q, repo_path)

            filtered = [r for r in results if r.metadata["function"] in expanded]
            funcs = [r.metadata["function"] for r in filtered]

            context = build_compressed_context(filtered)

            ans = generate_answer(q, context, expanded, "")

            recall = retrieval_recall(t.get("expected_keywords", []), funcs)
            judge = judge_explanation(q, ans, context)

            print("recall:", recall)
            print("judge:", judge)

        else:
            out = debugger_agent(q, "")
            judge = judge_debugger(out, t.get("expected_action"))

            print("output:", out)
            print("judge:", judge)


if __name__ == "__main__":
    run_eval(input("repo path: "))