import json

from ingestion.index import index_repo
from retrieval.query import search_code
from agents.context_extender import build_compressed_context
from agents.reasoner import generate_answer
from router import route_query

from eval.judge import judge_explanation
from eval.metrics import retrieval_recall


def run_eval(repo_path):
    index_repo(repo_path)

    with open("eval/test_cases.json") as f:
        tests = json.load(f)

    recalls = []
    correctness = []

    for t in tests:
        q = t["query"]

        print("\n---")
        print(q)

        route = route_query(q)
        print("route:", route)

        # search_code already returns the curated, ranked functions.
        results, expanded = search_code(q, repo_path)
        funcs = [r.metadata["function"] for r in results]

        context = build_compressed_context(results)
        ans = generate_answer(q, context, expanded, "")

        recall = retrieval_recall(t.get("expected_keywords", []), funcs)
        judge = judge_explanation(q, ans, context)

        recalls.append(recall)
        if isinstance(judge, dict) and "correctness" in judge:
            correctness.append(judge["correctness"])

        print("recall:", recall)
        print("judge:", judge)

    # -------- AGGREGATE SUMMARY --------
    def avg(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    print("\n=== SUMMARY ===")
    print(f"explanation cases : {len(recalls)}")
    print(f"mean recall       : {avg(recalls)}")
    print(f"mean correctness  : {avg(correctness)} (0-5)")


if __name__ == "__main__":
    run_eval(input("repo path: "))
