def retrieval_recall(expected_keywords, retrieved_funcs):
    if not expected_keywords:
        return 0.0

    hits = 0
    for keyword in expected_keywords:
        for func in retrieved_funcs:
            if keyword.lower() in func.lower():
                hits += 1
                break

    return hits / len(expected_keywords)