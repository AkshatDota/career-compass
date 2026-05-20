"""Unit tests for the adaptive question engine (app/questions.py)"""
import json
import pytest
from app.questions import (
    get_question_sequence,
    get_next_question,
    BASE_QUESTIONS,
    ADAPTIVE_QUESTIONS,
    ALL_QUESTIONS_BY_ID,
)


def _answered(question_id, answer):
    return {"question_id": question_id, "answer": answer}


class TestGetQuestionSequence:
    def test_base_sequence_without_q1_answer(self):
        seq = get_question_sequence([])
        assert seq == ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]

    def test_single_area_injects_one_followup(self):
        seq = get_question_sequence([_answered("q1", json.dumps(["Technology"]))])
        assert "q_tech" in seq
        assert seq.index("q_tech") == seq.index("q1") + 1

    def test_two_areas_inject_two_followups(self):
        seq = get_question_sequence([_answered("q1", json.dumps(["Technology", "Business"]))])
        assert "q_tech" in seq
        assert "q_biz" in seq
        assert seq.index("q_tech") < seq.index("q_biz")

    def test_all_seven_areas_injects_seven_followups(self):
        areas = ["Technology", "Business", "Healthcare", "Creative Arts",
                 "Education", "Law & Policy", "Science & Research"]
        seq = get_question_sequence([_answered("q1", json.dumps(areas))])
        assert len(seq) == 8 + 7  # 8 base + 7 adaptive
        for qid in ["q_tech", "q_biz", "q_health", "q_creative", "q_edu", "q_law", "q_sci"]:
            assert qid in seq

    def test_base_questions_always_at_end(self):
        seq = get_question_sequence([_answered("q1", json.dumps(["Technology"]))])
        base_tail = seq[seq.index("q2"):]
        assert base_tail == ["q2", "q3", "q4", "q5", "q6", "q7", "q8"]

    def test_unrecognised_area_does_not_inject(self):
        seq = get_question_sequence([_answered("q1", json.dumps(["Something Unknown"]))])
        assert seq == ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]

    def test_followup_order_matches_area_order(self):
        # Business comes before Technology alphabetically, but our order is Tech first
        seq = get_question_sequence([_answered("q1", json.dumps(["Business", "Technology"]))])
        assert seq.index("q_tech") < seq.index("q_biz")

    def test_plain_string_answer_for_q1(self):
        # Frontend may send a plain string instead of JSON array
        seq = get_question_sequence([_answered("q1", "Technology")])
        assert "q_tech" in seq


class TestGetNextQuestion:
    def test_first_call_returns_q1(self):
        q, cur, total = get_next_question([])
        assert q is not None
        assert q["id"] == "q1"
        assert cur == 1
        assert total == 8

    def test_returns_none_when_all_answered(self):
        answered = [_answered(qid, "x") for qid in
                    ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]]
        q, _, _ = get_next_question(answered)
        assert q is None

    def test_progress_current_increments(self):
        answered = [_answered("q1", "x")]
        _, cur, _ = get_next_question(answered)
        assert cur == 2

    def test_total_grows_with_adaptive_questions(self):
        answered = [_answered("q1", json.dumps(["Technology", "Business"]))]
        _, _, total = get_next_question(answered)
        assert total == 10  # 8 base + 2 adaptive

    def test_adaptive_question_returned_after_q1(self):
        answered = [_answered("q1", json.dumps(["Healthcare"]))]
        q, _, _ = get_next_question(answered)
        assert q["id"] == "q_health"

    def test_question_has_required_fields(self):
        q, _, _ = get_next_question([])
        for field in ("id", "text", "type", "options"):
            assert field in q


class TestQuestionBank:
    def test_base_questions_count(self):
        assert len(BASE_QUESTIONS) == 8

    def test_adaptive_questions_count(self):
        assert len(ADAPTIVE_QUESTIONS) == 7

    def test_all_base_questions_have_required_fields(self):
        for q in BASE_QUESTIONS:
            for field in ("id", "text", "type", "options"):
                assert field in q, f"Question {q.get('id')} missing field: {field}"
            assert len(q["options"]) >= 2

    def test_all_adaptive_questions_have_required_fields(self):
        for area, q in ADAPTIVE_QUESTIONS.items():
            for field in ("id", "text", "type", "options"):
                assert field in q, f"Adaptive '{area}' missing field: {field}"

    def test_all_question_ids_unique(self):
        all_ids = [q["id"] for q in BASE_QUESTIONS] + [q["id"] for q in ADAPTIVE_QUESTIONS.values()]
        assert len(all_ids) == len(set(all_ids)), "Duplicate question IDs found"

    def test_all_questions_indexed_in_all_questions_by_id(self):
        for q in BASE_QUESTIONS:
            assert q["id"] in ALL_QUESTIONS_BY_ID
        for q in ADAPTIVE_QUESTIONS.values():
            assert q["id"] in ALL_QUESTIONS_BY_ID
