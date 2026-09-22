import pytest
import json
from services.communication_service import communication_service


def test_wpm_calculation():
    # 26 words in 12 seconds = (26 / (12/60)) = 130 WPM
    sample_text = "Polymorphism allows objects to take many forms. In Java compile-time polymorphism is achieved via method overloading and runtime polymorphism is achieved through method overriding in inheritance."
    result = communication_service.analyze_communication(sample_text, duration_seconds=12.0)
    
    assert result["speaking_speed_wpm"] > 0
    assert 120 <= result["speaking_speed_wpm"] <= 140
    assert result["word_count"] >= 20


def test_filler_word_detection():
    # Text with intentional fillers: um, uh, basically, like
    sample_text = "I think, um, basically polymorphism is, uh, like when a class acquires properties."
    result = communication_service.analyze_communication(sample_text, duration_seconds=10.0)

    assert result["filler_count"] >= 3
    breakdown = json.loads(result["filler_breakdown"])
    assert "um" in breakdown or "umm" in breakdown
    assert "basically" in breakdown
    assert "like" in breakdown


def test_zero_fillers_boosts_communication_score():
    clean_text = "Polymorphism enables an entity such as a variable, function, or object to have more than one form. For example, in Java we override methods."
    result = communication_service.analyze_communication(clean_text, duration_seconds=15.0)

    assert result["filler_count"] == 0
    assert result["communication_score"] >= 7.0


def test_structure_scoring():
    structured_text = "Inheritance is defined as a mechanism where a child class acquires properties. This works because the JVM resolves references. For example, Dog inherits from Animal. Therefore, code reusability is maximized."
    result = communication_service.analyze_communication(structured_text, duration_seconds=20.0)

    assert result["structure_score"] >= 8.0
    assert result["structure_details"]["definition"] is True
    assert result["structure_details"]["example"] is True
