"""Unit tests for app/prompt_builder.py"""
import json
from app.prompt_builder import build_prompt


def _row(question_id, answer, question_text=None):
    return {"question_id": question_id, "answer": answer, "question_text": question_text}


class TestBuildPrompt:
    def test_returns_two_strings(self):
        system, user = build_prompt([_row("q1", "Technology")])
        assert isinstance(system, str)
        assert isinstance(user, str)

    def test_system_prompt_contains_core_content(self):
        system, _ = build_prompt([_row("q1", "Technology")])
        assert "BCA" in system
        assert "career counsellor" in system

    def test_system_prompt_uses_name_and_female_pronouns(self):
        rows = [
            _row("user_name",   "Nandini"),
            _row("user_gender", "female"),
            _row("q1",          "Technology"),
        ]
        system, user = build_prompt(rows)
        assert "Nandini" in system
        assert "she" in system or "her" in system
        assert "Nandini" in user  # name_ref used in user prompt

    def test_system_prompt_uses_male_pronouns(self):
        rows = [
            _row("user_name",   "Rohan"),
            _row("user_gender", "male"),
            _row("q1",          "Technology"),
        ]
        system, _ = build_prompt(rows)
        assert "Rohan" in system
        assert "he" in system or "him" in system

    def test_system_prompt_no_name_is_warm(self):
        system, _ = build_prompt([_row("q1", "Technology")])
        assert "warmly" in system or "warm" in system

    def test_name_gender_rows_excluded_from_qa_section(self):
        rows = [
            _row("user_name",   "Nandini"),
            _row("user_gender", "female"),
            _row("q1",          "Technology"),
        ]
        _, user = build_prompt(rows)
        assert "user_name" not in user
        assert "user_gender" not in user

    def test_user_prompt_contains_answer(self):
        _, user = build_prompt([_row("q1", "Technology")])
        assert "Technology" in user

    def test_uses_stored_question_text_over_bank_lookup(self):
        _, user = build_prompt([_row("q1", "Art", question_text="My custom question text?")])
        assert "My custom question text?" in user

    def test_falls_back_to_bank_text_when_no_stored_text(self):
        _, user = build_prompt([_row("q1", "Technology", question_text=None)])
        # q1 from the bank has this text
        assert "Which broad areas excite you" in user

    def test_unknown_question_id_uses_id_as_label(self):
        _, user = build_prompt([_row("custom_q", "Some answer", question_text=None)])
        assert "custom_q" in user

    def test_multi_select_answer_formatted_with_commas(self):
        _, user = build_prompt([_row("subjects", json.dumps(["Coding", "Math"]), None)])
        assert "Coding" in user
        assert "Math" in user

    def test_multiple_answers_all_appear(self):
        rows = [
            _row("q1", "Technology", "What excites you?"),
            _row("q2", "Startup",    "Preferred environment?"),
        ]
        _, user = build_prompt(rows)
        assert "What excites you?" in user
        assert "Preferred environment?" in user
        assert "Technology" in user
        assert "Startup" in user

    def test_prompt_requests_json_only(self):
        _, user = build_prompt([_row("q1", "Technology")])
        assert "ONLY valid JSON" in user or "only valid JSON" in user.lower()

    def test_prompt_contains_json_schema_fields(self):
        _, user = build_prompt([_row("q1", "Technology")])
        for field in ("title", "tagline", "why_it_fits", "salary", "skills_to_build",
                      "roadmap", "top_companies", "summary"):
            assert field in user, f"Schema field '{field}' missing from prompt"
