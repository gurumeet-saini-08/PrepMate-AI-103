import pytest
from services.ai_agent_service import ai_agent_service


def test_initial_question_generation():
    q = ai_agent_service.generate_first_question(
        role="Software Developer",
        difficulty="Intermediate",
        skills=["Java", "DSA"],
    )
    assert q is not None
    assert "question_text" in q
    assert len(q["question_text"]) > 15
    assert "expected_concepts" in q


def test_heuristic_response_evaluation():
    question = "What is polymorphism in Java?"
    expected = "method overloading, method overriding, runtime polymorphism, compile-time polymorphism"
    student_answer = "Polymorphism means taking many forms. In Java, compile-time polymorphism is done with method overloading, while runtime polymorphism uses method overriding and dynamic method dispatch. For example, a Shape class with a draw method."

    eval_result = ai_agent_service.evaluate_response(question, expected, student_answer)

    assert "correctness_score" in eval_result
    assert eval_result["correctness_score"] >= 7.0
    assert "strengths" in eval_result
    assert "improvements" in eval_result


def test_agent_decision_transitions_from_intro_to_technical():
    decision = ai_agent_service.decide_next_step(
        current_question_index=1,
        total_questions=3,
        role="Software Developer",
        current_question="Could you please introduce yourself?",
        transcript="Hello, I am a Computer Science student interested in Software Development.",
        correctness_score=8.5,
        comm_metrics={"communication_score": 8.0, "filler_count": 0},
        current_question_type="intro",
    )
    assert decision["action"] == "continue"
    assert decision["decision_type"] == "transition_technical"
    assert "transition" in decision["reason"].lower()


def test_agent_decision_escalate_on_strong_performance():
    # Technical question (Q2) with Correctness = 9.0, Communication = 8.5 -> Should ESCALATE
    decision = ai_agent_service.decide_next_step(
        current_question_index=2,
        total_questions=3,
        role="Software Developer",
        current_question="What is polymorphism?",
        transcript="Complete accurate explanation.",
        correctness_score=9.0,
        comm_metrics={"communication_score": 8.5, "filler_count": 0},
        current_question_type="core",
    )

    assert decision["action"] == "continue"
    assert decision["decision_type"] == "escalate"
    assert "escalat" in decision["reason"].lower()


def test_agent_decision_simplify_on_weak_performance():
    # Technical question (Q2) with Correctness = 3.5 -> Should SIMPLIFY
    decision = ai_agent_service.decide_next_step(
        current_question_index=2,
        total_questions=3,
        role="Software Developer",
        current_question="What is polymorphism?",
        transcript="I don't know.",
        correctness_score=3.5,
        comm_metrics={"communication_score": 5.0, "filler_count": 2},
        current_question_type="core",
    )

    assert decision["action"] == "continue"
    assert decision["decision_type"] == "simplify"
    assert "real-world analogy" in decision["reason"].lower() or "scaffold" in decision["reason"].lower()


def test_agent_decision_completes_when_limit_reached():
    decision = ai_agent_service.decide_next_step(
        current_question_index=3,
        total_questions=3,
        role="Software Developer",
        current_question="Final question",
        transcript="Good answer.",
        correctness_score=8.0,
        comm_metrics={"communication_score": 8.0, "filler_count": 1},
    )

    assert decision["action"] == "complete"


def test_heuristic_intro_response_evaluation():
    question = "Welcome! Could you please introduce yourself and share your background?"
    expected = "clear introduction, educational or technical background, motivation for role, key skills or projects, structured delivery"
    student_intro = (
        "Hello, my name is Gurumeet. I am a final-year Computer Science student at Chitkara University. "
        "I have worked on several software development projects using Java and Python, and I am passionate "
        "about building user-friendly applications. I am excited to interview for this role today."
    )

    eval_result = ai_agent_service.evaluate_response(
        question_text=question,
        expected_concepts=expected,
        student_transcript=student_intro,
        question_type="intro",
    )

    assert "correctness_score" in eval_result
    assert eval_result["correctness_score"] >= 8.0
    assert "strengths" in eval_result
    assert "improvements" in eval_result
    assert "model_answer" in eval_result


def test_beginner_difficulty_calibration():
    # Verify beginner initial question
    q1 = ai_agent_service.generate_first_question(
        role="Software Developer",
        difficulty="Beginner",
        skills=["Python"],
    )
    assert q1["question_type"] == "intro"
    assert q1["difficulty_level"] == "Beginner"
    assert "introduce" in q1["question_text"].lower()

    # Verify beginner transition technical question is fundamental
    q2_decision = ai_agent_service.decide_next_step(
        current_question_index=1,
        total_questions=3,
        role="Software Developer",
        current_question=q1["question_text"],
        transcript="Hello, I am a beginner programmer learning Python.",
        correctness_score=8.0,
        comm_metrics={"communication_score": 8.0, "filler_count": 0},
        current_question_type="intro",
        difficulty="Beginner",
    )
    assert q2_decision["decision_type"] == "transition_technical"
    next_q = q2_decision["next_question"]
    assert next_q is not None
    assert next_q["difficulty_level"] == "Beginner"
    # Verify question is simple (variable/constant/data types or basic function, NOT vtable or dynamic dispatch)
    assert "vtable" not in next_q["question_text"].lower()
    assert "polymorphism" not in next_q["question_text"].lower()


def test_synonym_evaluation_earns_high_score():
    # Expected concepts has "rows, columns, records, fields"
    question = "What is a database table, and what is the difference between a row and a column?"
    expected = "table, rows, columns, records, fields, data organization"
    
    # Student explains using synonyms: "grid", "entries", "attributes", "properties" instead of exact tokens
    student_answer_synonyms = (
        "A database table is like a structured grid used to organize information. "
        "Each horizontal entry represents an individual item or user, while the vertical attributes "
        "or properties define what kind of data is stored, such as a name or email address. "
        "This helps keep all related data organized in one place."
    )

    eval_result = ai_agent_service.evaluate_response(
        question_text=question,
        expected_concepts=expected,
        student_transcript=student_answer_synonyms,
        difficulty="Intermediate",
    )

    # Previously this scored 3.5 - 4.5; under the new semantic engine it must be >= 8.0!
    assert eval_result["correctness_score"] >= 8.0
    assert "strengths" in eval_result
    assert len(eval_result["strengths"]) > 10


def test_brief_response_still_receives_low_score():
    question = "What is polymorphism?"
    expected = "method overloading, method overriding, runtime polymorphism"
    brief_answer = "It is code."

    eval_result = ai_agent_service.evaluate_response(
        question_text=question,
        expected_concepts=expected,
        student_transcript=brief_answer,
    )

    assert eval_result["correctness_score"] <= 3.0


