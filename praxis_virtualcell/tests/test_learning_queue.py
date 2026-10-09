"""Tests for learning queue."""
from praxis_virtualcell.active_learning.learning_queue import LearningQueue, LearningQueueItem


def _item(cand, gain, module="genetic_hub"):
    return LearningQueueItem(candidate=cand, module=module, information_gain=gain,
                             drivers=["disagreement_high"], rationale="x")


def test_items_sorted_by_gain_desc():
    q = LearningQueue(items=[_item("a", 0.3), _item("b", 0.9), _item("c", 0.6)])
    gains = [it.information_gain for it in q.items]
    assert gains == sorted(gains, reverse=True)
    assert q.items[0].candidate == "b"


def test_empty_queue_has_note_not_fabricated():
    q = LearningQueue(items=[], notes=["no_actionable_candidates"])
    assert q.items == []
    assert "no_actionable_candidates" in q.notes


def test_to_dict_serializable():
    q = LearningQueue(items=[_item("a", 0.9)], notes=["n1"])
    d = q.to_dict()
    assert d["items"][0]["candidate"] == "a"
    assert d["items"][0]["information_gain"] == 0.9
    assert d["items"][0]["drivers"] == ["disagreement_high"]
    assert d["notes"] == ["n1"]
    import json
    json.dumps(d)


def test_item_to_dict_keys():
    d = _item("a", 0.5).to_dict()
    assert set(d) == {"candidate", "module", "information_gain", "drivers", "rationale"}


def test_stable_order_for_equal_gain():
    """Verify stable order for equal gain."""
    q1 = LearningQueue(items=[_item("a", 0.5, "genetic_hub"), _item("b", 0.5, "stress_processor")])
    q2 = LearningQueue(items=[_item("a", 0.5, "genetic_hub"), _item("b", 0.5, "stress_processor")])
    assert [it.candidate for it in q1.items] == [it.candidate for it in q2.items]
