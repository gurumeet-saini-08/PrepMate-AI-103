import re
import json


class CommunicationService:
    """
    Analyzes delivery aspects of the candidate's speech:
    - Words Per Minute (WPM)
    - Filler word detection & itemized breakdown
    - Pause / hesitation detection
    - Fluency rating
    - Answer structure scoring (Beginning, Explanation, Example, Conclusion)
    - Combined communication score (0 to 10 scale)
    """

    FILLER_PATTERNS = [
        r"\bum+\b",
        r"\buh+\b",
        r"\ber+\b",
        r"\bah+\b",
        r"\blike\b",
        r"\bbasically\b",
        r"\bactually\b",
        r"\bliterally\b",
        r"\byou know\b",
        r"\bsort of\b",
        r"\bkind of\b",
        r"\bi mean\b",
        r"\bright\b",
    ]

    STRUCTURE_MARKERS = {
        "definition": [
            "is defined as", "refers to", "means", "is a mechanism", "is a concept",
            "is when", "stands for", "essentially", "in simple terms"
        ],
        "explanation": [
            "because", "reason", "works by", "allows us to", "under the hood",
            "firstly", "furthermore", "specifically", "how it works"
        ],
        "example": [
            "for example", "for instance", "such as", "like in", "consider a case",
            "in java", "in python", "in sql", "suppose we have", "e.g."
        ],
        "conclusion": [
            "therefore", "hence", "in conclusion", "to summarize", "overall",
            "that is why", "ultimately", "as a result"
        ],
    }

    def analyze_communication(self, transcript: str, duration_seconds: float = 0.0) -> dict:
        """
        Analyzes a candidate's spoken response transcript and speaking duration.
        """
        cleaned_text = transcript.strip().lower()
        words = re.findall(r"\b[\w'-]+\b", cleaned_text)
        word_count = len(words)

        # Estimate duration if 0 (assume average baseline 130 WPM if no audio time passed)
        if duration_seconds <= 0:
            duration_seconds = max(5.0, (word_count / 130.0) * 60.0) if word_count > 0 else 5.0

        duration_minutes = max(0.05, duration_seconds / 60.0)
        wpm = round(word_count / duration_minutes, 1) if word_count > 0 else 0.0

        # Filler Words Detection
        filler_breakdown = {}
        total_fillers = 0

        for pattern in self.FILLER_PATTERNS:
            matches = re.findall(pattern, cleaned_text)
            if matches:
                key = matches[0].lower()
                count = len(matches)
                filler_breakdown[key] = filler_breakdown.get(key, 0) + count
                total_fillers += count

        # Pause / Hesitation Detection (detect ellipses, stutter hyphens, or prolonged silence ratio)
        pause_count = len(re.findall(r"\.{2,}|\b-\b", transcript))
        # Add pause estimates if candidate spoke very few words over long time
        if duration_seconds > 15 and wpm < 90 and word_count > 0:
            estimated_long_pauses = int((duration_seconds - (word_count / 130 * 60)) // 5)
            pause_count = max(pause_count, estimated_long_pauses)

        # Fluency Rating
        filler_density = (total_fillers / word_count) if word_count > 0 else 0.0
        if filler_density < 0.03 and 115 <= wpm <= 160:
            fluency = "Excellent"
        elif filler_density < 0.07 and 100 <= wpm <= 170:
            fluency = "Good"
        elif filler_density < 0.12 or 85 <= wpm < 100 or 170 < wpm <= 185:
            fluency = "Moderate"
        else:
            fluency = "Needs Improvement"

        # Structure Analysis
        structure_hits = {
            category: any(marker in cleaned_text for marker in markers)
            for category, markers in self.STRUCTURE_MARKERS.items()
        }
        structure_score = 4.0  # base starting score
        if structure_hits["definition"]:
            structure_score += 2.0
        if structure_hits["explanation"]:
            structure_score += 1.5
        if structure_hits["example"]:
            structure_score += 2.0
        if structure_hits["conclusion"]:
            structure_score += 0.5
        structure_score = min(10.0, round(structure_score, 1))

        # Overall Communication Score Calculation (0 - 10)
        # 1. WPM Score (ideal 120-150): up to 3.5 points
        if 120 <= wpm <= 150:
            wpm_score = 3.5
        elif 100 <= wpm < 120 or 150 < wpm <= 165:
            wpm_score = 2.8
        elif 80 <= wpm < 100 or 165 < wpm <= 180:
            wpm_score = 2.0
        else:
            wpm_score = 1.0 if word_count > 0 else 0.0

        # 2. Filler Penalty: up to 3.5 points
        if total_fillers == 0:
            filler_score = 3.5
        elif total_fillers <= 2:
            filler_score = 2.8
        elif total_fillers <= 4:
            filler_score = 2.0
        elif total_fillers <= 6:
            filler_score = 1.2
        else:
            filler_score = 0.5

        # 3. Structure contribution: up to 3.0 points
        structure_component = round((structure_score / 10.0) * 3.0, 1)

        comm_score = round(min(10.0, max(1.0, wpm_score + filler_score + structure_component)), 1)
        if word_count < 5:
            comm_score = 2.0  # Very brief/empty response penalty

        # Tailored Feedback Generation
        feedback_notes = []
        if wpm < 100:
            feedback_notes.append(f"Speaking speed was slightly slow ({wpm} WPM). Aim for a conversational 120-140 WPM.")
        elif wpm > 165:
            feedback_notes.append(f"Speaking speed was fast ({wpm} WPM). Slow down slightly to emphasize key technical terms.")
        else:
            feedback_notes.append(f"Great speaking pace ({wpm} WPM) within the professional interview sweet spot.")

        if total_fillers > 3:
            top_fillers = sorted(filler_breakdown.items(), key=lambda x: x[1], reverse=True)
            top_words = ", ".join([f"'{k}' ({v}x)" for k, v in top_fillers[:2]])
            feedback_notes.append(f"Detected {total_fillers} filler words ({top_words}). Practice silent 1-second pauses instead.")
        elif total_fillers > 0:
            feedback_notes.append(f"Low filler usage ({total_fillers} fillers). Keep maintaining this verbal discipline.")
        else:
            feedback_notes.append("Zero filler words detected! Excellent articulation and poise.")

        if not structure_hits["example"]:
            feedback_notes.append("Tip: Backing up your explanation with a concrete code or real-world example elevates technical depth.")

        return {
            "speaking_speed_wpm": wpm,
            "word_count": word_count,
            "duration_seconds": round(duration_seconds, 1),
            "filler_count": total_fillers,
            "filler_breakdown": json.dumps(filler_breakdown),
            "pause_count": pause_count,
            "fluency_rating": fluency,
            "structure_score": structure_score,
            "communication_score": comm_score,
            "structure_details": structure_hits,
            "feedback_notes": feedback_notes,
        }


# Singleton instance
communication_service = CommunicationService()
