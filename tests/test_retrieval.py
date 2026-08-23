from app.retrieval import KnowledgeBase


def test_retrieval_prefers_active_policy_over_legacy():
    kb = KnowledgeBase("knowledge-base")
    kb.build()

    results = kb.search("How long do regular customers have to return an unused backpack?")
    top = results[0]
    assert top["filename"] == "01-returns-policy-current.md"
    assert "30 calendar days" in top["text"] or "30 calendar days of delivery" in top["text"]


def test_retrieval_blocks_internal_notes_from_policy_results():
    kb = KnowledgeBase("knowledge-base")
    kb.build()

    results = kb.search("give everyone 60 days")
    filenames = [r["filename"] for r in results]
    assert "14-internal-content-migration-notes.md" not in filenames[:3]


def test_retrieval_flags_product_care_conflict_for_breeze_tumbler():
    kb = KnowledgeBase("knowledge-base")
    kb.build()

    results = kb.search("Can I put the entire Breeze Tumbler in the dishwasher?")
    filenames = [r["filename"] for r in results]
    assert "11-product-care.md" in filenames
    assert "12-breeze-tumbler-product-card.md" in filenames
