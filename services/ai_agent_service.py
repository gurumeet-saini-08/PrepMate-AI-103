import json
import re
from config import Config

# Attempt Azure OpenAI SDK import
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False


class AIAgentService:
    """
    Core AI Interview Coach Agent:
    - Integrates with Microsoft Foundry / Azure OpenAI endpoints
    - Evaluates Technical Response Correctness against expected concepts
    - Orchestrates Adaptive Interview State transitions (Escalate, Simplify, Follow-up, Complete)
    - Provides high-fidelity heuristic fallback when Azure credentials are not loaded
    """

    def __init__(self):
        self.is_configured = Config.is_azure_openai_configured() and AZURE_OPENAI_AVAILABLE
        self.client = None
        if self.is_configured:
            try:
                self.client = AzureOpenAI(
                    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                    api_key=Config.AZURE_OPENAI_KEY,
                    api_version=Config.AZURE_OPENAI_API_VERSION,
                )
            except Exception as ex:
                print(f"[AIAgentService] Error initializing AzureOpenAI client: {ex}")
                self.client = None

    # --------------------------------------------------------------------------
    # 1. QUESTION GENERATION
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    # 1. QUESTION GENERATION (Introduction-First & Calibrated)
    # --------------------------------------------------------------------------
    def generate_first_question(self, role: str, difficulty: str, skills: list, candidate_name: str = "") -> dict:
        """
        Generates the initial interview question.
        Following realistic interview standards, Question 1 is ALWAYS an
        Introduction & Background question tailored to the candidate's target role and level.
        """
        if self.client:
            try:
                name_clause = f"The candidate's name is {candidate_name}." if candidate_name else ""
                prompt = f"""
                You are a friendly, professional interviewer conducting a realistic job interview.
                {name_clause}

                Candidate information:
                - Target role: {role}
                - Interview difficulty: {difficulty}
                - Technical skills: {", ".join(skills) if skills else "General software development"}

                Your task is to ask the FIRST interview question.
                In a real job interview, the first question is ALWAYS a welcoming Introduction and Icebreaker question.

                GUIDELINES:
                - Ask ONE clear, natural opening question.
                - The language MUST be simple, conversational, and easy to understand when heard out loud.
                - Do NOT jump straight into complex technical trivia or code on Question 1.
                - Tailor the question to the selected difficulty and role:
                  * Beginner: Warm and encouraging. Ask them to briefly introduce themselves, what sparked their interest in {role}, and what basic technologies or topics they enjoy learning.
                  * Intermediate: Professional and conversational. Ask them to introduce themselves and briefly highlight their background and a relevant project or technology they have worked with.
                  * Advanced: Direct and engaging. Ask them to introduce themselves, outline their engineering journey, and briefly share a challenging technical project or architecture they have worked on.
                - Keep the question conversational and easy to answer verbally in 45-90 seconds.
                - Return ONLY valid JSON in exactly this format:

                {{
                    "question": "The opening introduction question",
                    "expected_concepts": "clear introduction, educational or technical background, motivation for role, key skills or projects, structured delivery",
                    "question_type": "intro",
                    "difficulty": "{difficulty}"
                }}
                """
                response = self.client.chat.completions.create(
                    model=Config.AZURE_OPENAI_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": "You are a professional, encouraging job interviewer. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content)
                return {
                    "question_text": data.get("question"),
                    "expected_concepts": data.get("expected_concepts", "clear introduction, background, role motivation, skills, structured delivery"),
                    "question_type": "intro",
                    "difficulty_level": difficulty,
                }
            except Exception as ex:
                print(f"[AIAgentService] Azure OpenAI generation error: {ex}. Using fallback curriculum.")

        # Heuristic Fallback Question Bank
        return self._get_fallback_initial_question(role, difficulty, candidate_name)

    # --------------------------------------------------------------------------
    # 2. RESPONSE EVALUATION (Intro vs Technical, Difficulty-Calibrated)
    # --------------------------------------------------------------------------
    def evaluate_response(
        self,
        question_text: str,
        expected_concepts: str,
        student_transcript: str,
        question_type: str = "core",
        difficulty: str = "Intermediate",
    ) -> dict:
        """
        Evaluates the student's answer:
        - If question_type is 'intro': evaluates self-presentation, clarity, relevance to role, and poise.
        - If technical question: evaluates conceptual correctness, depth, and relevance calibrated to difficulty.
        """
        is_intro = question_type == "intro" or "intro" in expected_concepts.lower()

        if self.client and student_transcript.strip():
            try:
                if is_intro:
                    prompt = (
                        f"You are an AI Interview Coach evaluating a candidate's introductory answer to the opening interview question.\n"
                        f"Interview Question: {question_text}\n"
                        f"Candidate Spoken Transcript: {student_transcript}\n\n"
                        f"Evaluate the candidate's self-introduction on:\n"
                        f"1. Clarity and structure (Greeting -> Background/Education -> Interests/Projects -> Closing enthusiasm)\n"
                        f"2. Relevance and motivation for the target role\n"
                        f"3. Professional tone, confidence, and articulation\n"
                        f"IMPORTANT: Do NOT penalize for lack of code syntax or technical algorithms. Evaluate this as an introductory elevator pitch.\n\n"
                        f"Return JSON strictly in this format:\n"
                        f"{{\n"
                        f'  "correctness_score": 8.5,\n'
                        f'  "strengths": "What the candidate communicated clearly and effectively in their introduction",\n'
                        f'  "missing_concepts": "Key elements they could add (e.g. mention a specific project or connect skills to the role)",\n'
                        f'  "qualitative_feedback": "Constructive 2-3 sentence coaching feedback on their introduction delivery",\n'
                        f'  "model_answer": "A concise 3-4 sentence ideal introduction demonstrating confidence and structure"\n'
                        f"}}"
                    )
                else:
                    diff_guidance = ""
                    if difficulty.lower() == "beginner":
                        diff_guidance = (
                            "DIFFICULTY: BEGINNER. Be encouraging and generous. Focus on whether the candidate understands the general intuition, "
                            "mechanism, or definition. Do NOT penalize the candidate for missing formal academic jargon, compiler internals, or complex architecture. "
                            "A clear, intuitive explanation in everyday language easily qualifies for 8.0 - 9.5."
                        )
                    elif difficulty.lower() == "advanced":
                        diff_guidance = (
                            "DIFFICULTY: ADVANCED. Evaluate architectural reasoning, concurrency awareness, and trade-offs. "
                            "Still prioritize conceptual accuracy and sound logic over rote keyword memorization."
                        )
                    else:
                        diff_guidance = (
                            "DIFFICULTY: INTERMEDIATE. Expect solid practical understanding of standard concepts, data structures, "
                            "and real-world trade-offs."
                        )

                    prompt = f"""
You are an AI Interview Coach evaluating a candidate's spoken technical answer.

Interview Question: {question_text}
Expected Concepts / Reference Topics: {expected_concepts}
Candidate Spoken Transcript: {student_transcript}
{diff_guidance}

CRITICAL SCORING PHILOSOPHY - CONCEPTUAL MEANING OVER EXACT KEYWORDS:
1. SEMANTIC EQUIVALENCE & SYNONYMS (MANDATORY RULE):
   - You MUST evaluate the candidate's CONCEPTUAL UNDERSTANDING and TECHNICAL ACCURACY, NOT exact word matching.
   - If the candidate explains the correct concept using DIFFERENT WORDS, SYNONYMS, PRACTICAL EXPLANATIONS, OR ANALOGIES rather than the exact phrases in "Expected Concepts", you MUST AWARD FULL CREDIT.
   - Examples:
     * Expected: "rows", "records" -> Candidate says: "entries", "data rows", "items in the table", "horizontal lines" => FULL CREDIT.
     * Expected: "columns", "fields" -> Candidate says: "attributes", "properties", "categories", "vertical values" => FULL CREDIT.
     * Expected: "variables vs constants" -> Candidate says: "a variable can change value as the code runs, but a constant stays fixed" => FULL CREDIT.
     * Expected: "functions" -> Candidate says: "blocks of code that do a specific task so we don't repeat code" => FULL CREDIT.
     * Expected: "compile-time vs runtime" -> Candidate says: "one is checked when the code is built or compiled, and the other happens while the program is actually running" => FULL CREDIT.
     * Expected: "B-Tree index" -> Candidate says: "a balanced tree structure that lets the database search fast in log time without scanning the whole table" => FULL CREDIT.
2. CONSTRUCTIVE COACHING ON TERMINOLOGY:
   - If the candidate explained the concept correctly in their own words but omitted formal technical buzzwords, award them a HIGH correctness score (e.g. 8.0 - 9.5).
   - In "missing_concepts", mention the standard industry terms solely as a helpful, constructive tip to sound more senior (e.g. "Great explanation! In interviews, you can also use the technical term 'overriding' to sound even sharper"), without docking their numerical score.
3. SPOKEN TRANSCRIPT TOLERANCE:
   - The candidate answered using their voice. Disregard minor speech-to-text transcription artifacts, conversational pauses, or informal phrasing. Focus on the core meaning.

SCORING ANCHORS (0.0 to 10.0 scale):
- 8.5 - 10.0 (Strong / Mastery): Clearly grasps the concept; explains the mechanism/idea correctly in their own words; provides a good solution or practical example.
- 7.0 - 8.4 (Good / Competent): Conveys the core correct idea well and provides a solid explanation, even if minor secondary nuances or formal buzzwords are omitted.
- 5.5 - 6.9 (Fair / Basic Understanding): Demonstrates foundational familiarity with partial accuracy, but the answer lacks clarity or depth.
- 3.5 - 5.4 (Developing / Gaps): Noticeable misconceptions, confusing logic, or missing the central point.
- 1.0 - 3.4 (Unanswered / Off-topic): Barely attempted, irrelevant, or completely incorrect.

Return JSON strictly in this format:
{{
  "correctness_score": 8.5,
  "strengths": "Specific accurate concepts and logic the candidate explained well",
  "missing_concepts": "Constructive professional terms or edge cases to consider",
  "qualitative_feedback": "Encouraging, constructive 2-3 sentence coaching feedback acknowledging their explanation",
  "model_answer": "Concise ideal answer in clear, accessible language"
}}
"""

                response = self.client.chat.completions.create(
                    model=Config.AZURE_OPENAI_DEPLOYMENT,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an objective, encouraging technical interview coach. "
                                "You evaluate candidate answers based on semantic conceptual accuracy, clarity of reasoning, "
                                "and practical problem solving—NOT exact word matching. Return only valid JSON."
                            ),
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                data = json.loads(response.choices[0].message.content)
                return {
                    "correctness_score": float(data.get("correctness_score", 7.5)),
                    "strengths": data.get("strengths", "Solid foundational communication demonstrated."),
                    "improvements": data.get("missing_concepts", "Consider incorporating industry-standard terms to anchor your explanation."),
                    "qualitative_feedback": data.get("qualitative_feedback", "Good explanation of key points."),
                    "model_answer": data.get("model_answer", "A comprehensive answer covers the main points clearly with a practical example."),
                }
            except Exception as ex:
                print(f"[AIAgentService] Azure OpenAI evaluation error: {ex}. Using fallback evaluator.")

        # Heuristic Rule-Based Evaluator Fallback
        if is_intro:
            return self._heuristic_evaluate_intro_response(question_text, expected_concepts, student_transcript)
        return self._heuristic_evaluate_response(question_text, expected_concepts, student_transcript, difficulty)

    # --------------------------------------------------------------------------
    # 3. ADAPTIVE AI AGENT DECISION ENGINE
    # --------------------------------------------------------------------------
    def decide_next_step(
        self,
        current_question_index: int,
        total_questions: int,
        role: str,
        current_question: str,
        transcript: str,
        correctness_score: float,
        comm_metrics: dict,
        current_question_type: str = "core",
        difficulty: str = "Intermediate",
    ) -> dict:
        """
        AI Agent Core Decision-Making:
        - If completing Question 1 (intro): transitions smoothly to the first core technical question.
        - For subsequent questions: evaluates (Correctness + Communication) to choose the strategy:
          * ESCALATE: Candidate excelled -> increase depth / explore trade-offs.
          * SIMPLIFY: Candidate struggled -> scaffold with an everyday real-world analogy.
          * STRUCTURE_FOLLOWUP: Hesitant or unstructured flow -> prompt for a step-by-step practical example.
          * PROGRESS_CORE: Balanced answer -> advance to next major curriculum topic.
          * COMPLETE: Reached total questions -> finalize interview.
        """
        if current_question_index >= total_questions:
            return {
                "action": "complete",
                "reason": "All planned interview questions have been completed.",
                "next_question": None,
            }

        comm_score = comm_metrics.get("communication_score", 7.0)
        fillers = comm_metrics.get("filler_count", 0)

        # Transition from Introduction to First Technical Question
        if current_question_type == "intro" or current_question_index == 1:
            decision_type = "transition_technical"
            reason = "Candidate introduction completed. Transitioning smoothly into the first core technical question tailored to the role."
        # 1. Candidate excelled technically and communicated clearly
        elif correctness_score >= 8.0 and comm_score >= 7.0:
            decision_type = "escalate"
            reason = "High technical accuracy and strong communication detected. Escalating to test deeper practical understanding."
        # 2. Candidate struggled with core concept
        elif correctness_score <= 5.0:
            decision_type = "simplify"
            reason = "Candidate had gaps in the concept. Scaffolding with an intuitive, real-world analogy question."
        # 3. High fillers or low communication score
        elif fillers >= 4 or comm_score < 6.0:
            decision_type = "structure_followup"
            reason = "Communication delivery had hesitations or unstructured flow. Follow-up asks for a step-by-step practical scenario to build poise."
        # 4. Balanced answer
        else:
            decision_type = "progress_core"
            reason = "Good core answer. Advancing to the next technical topic in the curriculum."

        # Generate next question via Azure OpenAI or Heuristic Engine
        next_q = self._generate_adaptive_question(
            role=role,
            current_question=current_question,
            decision_type=decision_type,
            question_index=current_question_index + 1,
            difficulty=difficulty,
        )

        return {
            "action": "continue",
            "decision_type": decision_type,
            "reason": reason,
            "next_question": next_q,
        }

    def _generate_adaptive_question(
        self,
        role: str,
        current_question: str,
        decision_type: str,
        question_index: int,
        difficulty: str = "Intermediate",
    ) -> dict:
        """Generates the next adaptive question based on agent decision with plain language and difficulty calibration."""
        if self.client:
            try:
                system_instruction = (
                    f"You are the adaptive AI Interview Agent for PrepMate.\n"
                    f"Role: {role}\n"
                    f"Difficulty: {difficulty}\n"
                    f"Previous Question: {current_question}\n"
                    f"Agent Directive: {decision_type.upper()}\n"
                )

                if decision_type == "transition_technical":
                    guide = (
                        f"The candidate has just introduced themselves. Now ask the FIRST core technical question for a {difficulty} level {role}. "
                        "Keep it welcoming, direct, and focused on essential principles."
                    )
                elif decision_type == "escalate":
                    guide = (
                        "Ask a deeper follow-up exploring practical application, trade-offs, or real-world behavior. "
                        "Keep the language plain and natural; avoid needlessly convoluted phrasing."
                    )
                elif decision_type == "simplify":
                    guide = (
                        "The candidate struggled. Ask an accessible question or invite them to explain the concept "
                        "using a simple, everyday real-world analogy."
                    )
                elif decision_type == "structure_followup":
                    guide = (
                        "Ask them to walk through a concrete, practical example or step-by-step workflow, "
                        "encouraging clear and structured communication."
                    )
                else:
                    guide = f"Introduce the next essential technical topic relevant to a {difficulty} {role}."

                difficulty_rules = ""
                if difficulty.lower() == "beginner":
                    difficulty_rules = """
                    CRITICAL BEGINNER CALIBRATION:
                    - The candidate is at BEGINNER level.
                    - Ask ONLY foundational, accessible questions (e.g. basic variables, simple functions, difference between array and list, what a loop is, simple HTTP GET vs POST, what a database table is).
                    - NEVER ask about low-level concurrency, vtables, internal memory pointers, microtasks, or B-Tree algorithms.
                    - The question MUST use simple, everyday conversational vocabulary that any student can easily understand when spoken.
                    """
                elif difficulty.lower() == "advanced":
                    difficulty_rules = """
                    ADVANCED CALIBRATION:
                    - Test architectural reasoning, concurrency, or performance trade-offs.
                    - Even for advanced concepts, phrase the question simply and directly in one or two clear sentences so it is easy to understand verbally.
                    """
                else:
                    difficulty_rules = """
                    INTERMEDIATE CALIBRATION:
                    - Test practical understanding of common data structures, standard APIs, OOP principles, or database queries.
                    - Keep the phrasing clear, practical, and conversational.
                    """

                prompt = f"""
                You are an adaptive AI interviewer conducting a realistic job interview.

                Candidate target role: {role}
                Interview difficulty: {difficulty}
                Previous interview question: {current_question}
                The interview agent directive: {decision_type}
                Current question number: {question_index}

                Directive Guide: {guide}

                {difficulty_rules}

                IMPORTANT REQUIREMENTS:
                - Ask exactly ONE question.
                - The language MUST be simple, clear, and easy to understand when spoken by an interviewer.
                - The candidate will answer by voice or text, so the question must be easy to answer verbally.
                - Keep the interview conversational and realistic.
                - Do NOT ask multi-part questions or combine several tasks into one.
                - Do NOT ask the candidate to write code, SQL scripts, or complete system designs.
                - Do not provide the answer or hints.

                Return ONLY valid JSON in exactly this format:

                {{
                    "question": "The next interview question",
                    "expected_concepts": "Important concepts that a good answer should cover",
                    "difficulty": "{difficulty}",
                    "question_type": "{decision_type}"
                }}
                """
                response = self.client.chat.completions.create(
                    model=Config.AZURE_OPENAI_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                )
                data = json.loads(response.choices[0].message.content)
                return {
                    "question_text": data.get("question"),
                    "expected_concepts": data.get("expected_concepts"),
                    "question_type": decision_type,
                    "difficulty_level": data.get("difficulty", difficulty),
                    "order_index": question_index,
                }
            except Exception as ex:
                print(f"[AIAgentService] Azure OpenAI adaptive question error: {ex}")

        # Heuristic Adaptive Question Selection
        return self._get_fallback_adaptive_question(role, current_question, decision_type, question_index, difficulty)

    # --------------------------------------------------------------------------
    # HEURISTIC / FALLBACK ENGINES (Guarantees zero demo failures)
    # --------------------------------------------------------------------------
    def _heuristic_evaluate_intro_response(self, question_text: str, expected_concepts: str, transcript: str) -> dict:
        """Evaluates student self-introduction when offline or in fallback mode."""
        cleaned = transcript.lower().strip()
        words = re.findall(r"\b\w+\b", cleaned)
        word_count = len(words)

        if word_count < 6:
            return {
                "correctness_score": 3.0,
                "strengths": "Initial introduction started.",
                "improvements": "Your introduction was very brief. Include your name, academic background, key skills, and what excites you about this role.",
                "qualitative_feedback": "A strong interview introduction usually takes 45-60 seconds. Share your background and what motivated you to pursue this career path.",
                "model_answer": "Hello! I am a Computer Science student with a strong interest in software development. I have been building projects with Python and Java, and I am excited about this role because I enjoy solving real-world problems through clean code.",
            }

        # Check for key introduction elements
        intro_markers = [
            "name", "i am", "i'm", "student", "college", "university", "background",
            "project", "technology", "skills", "learned", "interested", "passionate",
            "developer", "engineer", "build", "worked", "experience", "looking forward",
            "python", "java", "web", "data", "software", "excited", "degree"
        ]
        matched_markers = [m for m in intro_markers if m in cleaned]
        marker_score = min(4.5, (len(matched_markers) / 4.0) * 4.5)

        # Length score (target 30 - 80 words)
        if 25 <= word_count <= 120:
            length_score = 4.0
        elif word_count > 120:
            length_score = 3.5  # Slightly verbose
        else:
            length_score = 2.5

        # Structure bonus (greeting or conclusion)
        structure_bonus = 1.0 if any(g in cleaned for g in ["hello", "hi", "good morning", "good afternoon", "thank you", "thanks"]) else 0.5

        final_score = round(min(10.0, max(4.0, marker_score + length_score + structure_bonus)), 1)

        strengths = []
        if any(g in cleaned for g in ["hello", "hi", "good morning", "good afternoon"]):
            strengths.append("Started with a polite and professional greeting.")
        if any(x in cleaned for x in ["project", "built", "worked", "experience"]):
            strengths.append("Effectively highlighted practical project background.")
        if any(x in cleaned for x in ["passionate", "interested", "excited", "enjoy"]):
            strengths.append("Expressed genuine motivation and enthusiasm for the field.")
        if not strengths:
            strengths.append("Demonstrated clear verbal communication and self-awareness.")

        improvements = []
        if not any(x in cleaned for x in ["project", "built", "worked"]):
            improvements.append("Mention a standout project you enjoyed building to anchor your technical credibility.")
        if not any(x in cleaned for x in ["passionate", "interested", "excited"]):
            improvements.append("State specifically what draws you to this target role to show career alignment.")
        if word_count < 25:
            improvements.append("Elaborate slightly to give the interviewer a richer picture of your journey (aim for 40-70 words).")

        return {
            "correctness_score": final_score,
            "strengths": " ".join(strengths),
            "improvements": " ".join(improvements) if improvements else "Great introductory delivery; maintain this poise throughout the interview.",
            "qualitative_feedback": (
                f"You delivered a {'confident and structured' if final_score >= 8.0 else 'promising'} opening introduction. "
                "Keep this warm and professional momentum going as we transition into technical topics."
            ),
            "model_answer": (
                "Hi, thank you! I am a final-year Computer Science student passionate about software engineering. "
                "Over the past year, I have focused on building practical web and backend applications using Java and Python. "
                "I am particularly excited about this role because I love tackling collaborative engineering challenges and continuously learning new technologies."
            ),
        }

    # Comprehensive technical synonym and conceptual equivalent dictionary
    CONCEPT_SYNONYMS = {
        "table": ["table", "grid", "entity", "relation", "sheet", "database table", "structured data"],
        "rows": ["row", "rows", "record", "records", "entry", "entries", "tuple", "tuples", "item", "items", "horizontal"],
        "columns": ["column", "columns", "field", "fields", "attribute", "attributes", "property", "properties", "vertical", "header"],
        "variable": ["variable", "variables", "var", "container", "placeholder", "stores", "holding", "storage", "changeable", "value changes"],
        "constant": ["constant", "constants", "immutable", "cannot change", "fixed", "final", "const", "never changes", "read-only"],
        "function": ["function", "functions", "method", "methods", "procedure", "subroutine", "routine", "block of code", "modular", "reusable"],
        "loop": ["loop", "loops", "iteration", "iterate", "repeating", "repetition", "cycles", "while", "for", "again and again"],
        "polymorphism": ["polymorphism", "polymorphic", "many forms", "different forms", "overloading", "overriding", "dynamic dispatch", "behavior"],
        "overloading": ["overloading", "overload", "same name different parameters", "same method different arguments", "compile-time"],
        "overriding": ["overriding", "override", "child class replaces", "subclass implementation", "runtime", "dynamic method", "same signature"],
        "inheritance": ["inheritance", "inherit", "parent", "child", "subclass", "superclass", "extends", "base class", "derived class", "reuses code"],
        "encapsulation": ["encapsulation", "data hiding", "private", "public", "protect", "getters", "setters", "access modifiers", "bundle data"],
        "index": ["index", "indexes", "indices", "lookup", "b-tree", "btree", "faster search", "pointer", "speed up queries", "binary search"],
        "process": ["process", "processes", "program in execution", "isolated memory", "address space", "running instance"],
        "thread": ["thread", "threads", "lightweight", "shared memory", "concurrency", "parallel", "worker", "execution unit"],
        "api": ["api", "apis", "endpoint", "endpoints", "rest", "http", "service", "interface", "communication", "web service"],
        "get": ["get", "retrieve", "fetch", "read", "obtain", "requesting data", "querying", "pull"],
        "post": ["post", "send", "submit", "create", "insert", "payload", "body", "adding new", "push"],
        "join": ["join", "joins", "combine", "matching", "merge", "connecting tables", "linking", "inner join", "left join"],
        "supervised": ["supervised", "labeled", "labels", "ground truth", "known output", "training data", "targets"],
        "unsupervised": ["unsupervised", "unlabeled", "clustering", "patterns", "grouping", "no labels", "hidden structure"],
        "dom": ["dom", "document object model", "tree", "elements", "html nodes", "page structure", "document"],
        "event loop": ["event loop", "asynchronous", "async", "call stack", "queue", "callback", "non-blocking"],
        "stack": ["stack", "stack memory", "call stack", "lifo", "local variables", "function frames"],
        "heap": ["heap", "heap memory", "dynamic memory", "objects", "garbage collection", "allocation"],
    }

    def _heuristic_evaluate_response(self, question_text: str, expected_concepts: str, transcript: str, difficulty: str = "Intermediate") -> dict:
        """
        Evaluates student technical answer with fair semantic matching:
        - Recognizes conceptual equivalents, synonyms, and practical explanations
        - Awards fair scores for correct explanations rather than penalizing missing exact keywords
        - Calibrates scoring by difficulty level
        """
        cleaned = transcript.lower().strip()
        words = re.findall(r"\b\w+\b", cleaned)
        word_count = len(words)

        if word_count < 6:
            return {
                "correctness_score": 2.5,
                "strengths": "Answer was initiated.",
                "improvements": "The response was very brief. Elaborate on the core idea, how it works, and give a simple example.",
                "qualitative_feedback": "Your answer was very brief. In an interview, aim for 45-75 seconds of clear, structured explanation.",
                "model_answer": f"Expected coverage on: {expected_concepts}.",
            }

        expected_tokens = [t.strip().lower() for t in expected_concepts.split(",") if t.strip()]
        matched_concepts = []
        missing_terms = []

        # Semantic & Synonym Matching Engine
        for token in expected_tokens:
            # 1. Direct match
            if token in cleaned:
                matched_concepts.append(token)
                continue

            # 2. Check root/sub-words of the token (e.g. "overload" in "method overloading")
            token_words = token.split()
            direct_word_hit = any(tw in cleaned for tw in token_words if len(tw) >= 4)
            if direct_word_hit:
                matched_concepts.append(token)
                continue

            # 3. Synonym dictionary lookup
            synonym_hit = False
            for key, syn_list in self.CONCEPT_SYNONYMS.items():
                if key in token or any(tw in key for tw in token_words):
                    if any(syn in cleaned for syn in syn_list):
                        matched_concepts.append(token)
                        synonym_hit = True
                        break

            if not synonym_hit:
                missing_terms.append(token)

        # Base score calibrated to effort, length, and difficulty
        diff_lower = difficulty.lower()
        if word_count >= 20:
            base_score = 6.8 if diff_lower == "beginner" else (6.0 if diff_lower == "intermediate" else 5.5)
        elif 10 <= word_count < 20:
            base_score = 5.5 if diff_lower == "beginner" else (5.0 if diff_lower == "intermediate" else 4.5)
        else:
            base_score = 4.0

        # Concept match contribution (hitting 2-3 key concepts/synonyms gives max concept credit)
        target_concepts = max(1, min(3, len(expected_tokens)))
        coverage_ratio = len(matched_concepts) / target_concepts
        concept_points = min(2.5, coverage_ratio * 2.5)

        # Reasoning connector bonus (detects explanation logic)
        reasoning_markers = [
            "because", "means", "works by", "helps", "used to", "allows", "so that",
            "instead of", "which is", "in order to", "reason", "therefore", "difference is", "refers to"
        ]
        has_reasoning = any(rm in cleaned for rm in reasoning_markers)
        reasoning_bonus = 0.8 if has_reasoning else 0.0

        # Concrete example bonus
        example_markers = ["for example", "such as", "like", "instance", "consider", "in case", "example", "say we have", "suppose"]
        has_example = any(em in cleaned for em in example_markers)
        example_bonus = 0.8 if has_example else 0.0

        final_score = round(min(10.0, max(3.0, base_score + concept_points + reasoning_bonus + example_bonus)), 1)

        strengths_list = []
        if matched_concepts:
            strengths_list.append(f"Successfully conveyed core concepts and logic around: {', '.join(matched_concepts[:3])}.")
        if has_reasoning:
            strengths_list.append("Articulated clear cause-and-effect reasoning behind the concept.")
        if has_example:
            strengths_list.append("Anchored the explanation with a helpful practical example.")
        if not strengths_list:
            strengths_list.append("Maintained good conversational flow and addressed the question.")

        improvements_list = []
        if missing_terms:
            improvements_list.append(
                f"To sound even sharper, you can also weave in standard industry terminology: {', '.join(missing_terms[:3])}."
            )
        if not has_example:
            improvements_list.append("Backing up your answer with a quick concrete example will elevate your explanation.")

        return {
            "correctness_score": final_score,
            "strengths": " ".join(strengths_list),
            "improvements": " ".join(improvements_list) if improvements_list else "Clear and comprehensive answer. Maintain this structured delivery.",
            "qualitative_feedback": (
                f"You demonstrated good grasp on the topic. "
                f"{'Great job explaining the mechanics in your own words!' if final_score >= 7.5 else 'Focus on elaborating the underlying mechanisms step-by-step.'}"
            ),
            "model_answer": (
                f"A strong answer clearly defines the core concept in accessible terms, explains how it is used, "
                f"covers key points ({', '.join(expected_tokens[:4])}), and illustrates with a practical example."
            ),
        }

    def _get_fallback_initial_question(self, role: str, difficulty: str, candidate_name: str = "") -> dict:
        """Heuristic fallback for Question 1: Always a realistic, warm introduction question."""
        greeting = f"Hello {candidate_name}! " if candidate_name else "Hello! "
        diff_lower = difficulty.lower()

        if diff_lower == "beginner":
            q_text = (
                f"{greeting}Welcome to your mock interview for the {role} position. "
                "To get started, could you please introduce yourself, tell me a little about your background, "
                "and share what got you interested in this field?"
            )
        elif diff_lower == "advanced":
            q_text = (
                f"{greeting}Welcome to the interview for the {role} role. "
                "To kick things off, please introduce yourself, give a brief overview of your technical journey, "
                "and tell me about a key project or engineering challenge you've worked on recently."
            )
        else:
            # Intermediate default
            q_text = (
                f"{greeting}Welcome! To begin our interview for the {role} position, "
                "could you please introduce yourself and walk me through your background and a recent project you enjoyed working on?"
            )

        return {
            "question_text": q_text,
            "expected_concepts": "clear introduction, educational or technical background, motivation for role, key skills or projects, structured delivery",
            "question_type": "intro",
            "difficulty_level": difficulty,
        }

    def _get_fallback_adaptive_question(self, role: str, previous_q: str, decision_type: str, index: int, difficulty: str = "Intermediate") -> dict:
        """Heuristic adaptive questions calibrated by role, difficulty, and plain-language comprehension."""
        role_lower = role.lower()
        diff_lower = difficulty.lower()

        # Beginner question bank
        if diff_lower == "beginner":
            if decision_type == "transition_technical" or index == 2:
                if "data" in role_lower or "analyst" in role_lower:
                    q_text = "In simple terms, what is a database table, and what is the difference between a row and a column?"
                    concepts = "table, rows, columns, records, fields, data organization"
                elif "frontend" in role_lower or "web" in role_lower:
                    q_text = "In web development, what are HTML and CSS, and what is the basic job of each one?"
                    concepts = "HTML structure, CSS styling, tags, visual appearance, webpage layout"
                elif "ai" in role_lower or "ml" in role_lower:
                    q_text = "In simple terms, what is Machine Learning, and how is it different from normal computer programming?"
                    concepts = "learning from data, patterns, training, predictions, rule-based programming"
                else:
                    q_text = "In simple terms, what is the difference between a variable and a constant in programming, and why do we use data types?"
                    concepts = "variable value changes, constant cannot change, data types, memory, integer string boolean"
            elif decision_type == "simplify":
                q_text = "Think of a daily routine or chore you do repeatedly. How would you explain what a loop does in programming using that everyday example?"
                concepts = "repetition, condition, everyday analogy, repeating steps, stop condition"
            elif decision_type == "structure_followup":
                q_text = "Can you walk me through a simple, step-by-step example of how a function takes input, does something, and gives back a result?"
                concepts = "input parameters, function body, logic, return value, simple example"
            elif decision_type == "escalate":
                q_text = "Good job! Now, can you explain the difference between storing items in a simple Array versus a dynamic List?"
                concepts = "fixed size, dynamic resizing, elements, index access, adding removing items"
            else:
                # Progress core for beginner
                beginner_topics = [
                    ("What is a function or method in programming, and why is it helpful to break code into smaller functions?", "code reusability, readability, organization, testing, modular code"),
                    ("What is an if-else statement, and how does it help a program make decisions?", "conditional logic, true or false, decision making, execution branches"),
                    ("What is a loop (like a for or while loop), and can you give a simple example of when you would use one?", "iteration, repeated actions, for loop, while loop, condition"),
                ]
                picked = beginner_topics[(index - 1) % len(beginner_topics)]
                q_text, concepts = picked[0], picked[1]

        # Advanced question bank
        elif diff_lower == "advanced":
            if decision_type == "transition_technical" or index == 2:
                if "data" in role_lower or "analyst" in role_lower:
                    q_text = "How do database indexes improve query lookup performance, and what write overhead do they introduce during inserts and updates?"
                    concepts = "B-Tree index, read optimization, write overhead, table scans, indexing strategy"
                elif "frontend" in role_lower or "web" in role_lower:
                    q_text = "How does browser rendering optimization work (such as minimizing reflows and repaints), and how does a virtual DOM assist with this?"
                    concepts = "reflow, repaint, DOM reconciliation, virtual DOM, performance, batch updates"
                else:
                    q_text = "How does memory management work between the Stack and the Heap, and what triggers Garbage Collection in runtime environments like the JVM or Python?"
                    concepts = "stack memory, heap memory, reference counting, generational garbage collection, memory leaks"
            elif decision_type == "escalate":
                q_text = "What are race conditions in multithreaded systems, and how do synchronization mechanisms like mutexes or locks prevent data corruption?"
                concepts = "thread safety, race condition, mutual exclusion, locks, deadlock prevention"
            elif decision_type == "simplify":
                q_text = "Let's step back. Can you explain the core concept using an intuitive real-world analogy from everyday life?"
                concepts = "real-world analogy, intuitive relationship, everyday example, clear comparison"
            elif decision_type == "structure_followup":
                q_text = "Walk me through the concrete execution flow: what happens step-by-step from the initial function call to the final state?"
                concepts = "execution flow, call stack, state transition, step by step, edge cases"
            else:
                advanced_topics = [
                    ("What are database Indexes and how do B-Trees optimize query lookup times compared to a full table scan?", "B-Tree, lookup time, O(log n), write overhead, primary key index, range queries"),
                    ("Explain the difference between Process and Thread, and how inter-thread communication or synchronization prevents race conditions.", "shared memory, context switching, mutex, synchronization, deadlock, thread safety"),
                    ("What is the difference between REST API and GraphQL, and what problems does GraphQL solve regarding over-fetching?", "over-fetching, under-fetching, single endpoint, schema, query flexibility, HTTP methods"),
                ]
                picked = advanced_topics[(index - 1) % len(advanced_topics)]
                q_text, concepts = picked[0], picked[1]

        # Intermediate question bank (Default)
        else:
            if decision_type == "transition_technical" or index == 2:
                if "data" in role_lower or "analyst" in role_lower:
                    q_text = "What is the difference between an INNER JOIN and a LEFT JOIN in SQL, and when would you use each?"
                    concepts = "matching rows, NULL values, table relationships, left table data, join condition"
                elif "frontend" in role_lower or "web" in role_lower:
                    q_text = "What is the Document Object Model (DOM), and how does JavaScript interact with it on a webpage?"
                    concepts = "DOM tree, HTML elements, event listeners, dynamic UI, element selection"
                elif "ai" in role_lower or "ml" in role_lower:
                    q_text = "What is the difference between Supervised Learning and Unsupervised Learning, with a simple example of each?"
                    concepts = "labeled data, unlabeled data, classification, clustering, training features"
                else:
                    q_text = "What are the core principles of Object-Oriented Programming (OOP), and can you briefly explain what Encapsulation means?"
                    concepts = "encapsulation, abstraction, inheritance, polymorphism, data hiding, access modifiers"
            elif decision_type == "escalate":
                q_text = "Great answer! Can you explain the difference between an Abstract Class and an Interface, and when you would choose one over the other?"
                concepts = "multiple inheritance, default methods, state, abstract methods, design trade-offs"
            elif decision_type == "simplify":
                q_text = "Let's look at this from another angle. Can you explain that concept using a simple everyday analogy that anyone could understand?"
                concepts = "real-world analogy, intuitive comparison, everyday scenario, accessible explanation"
            elif decision_type == "structure_followup":
                q_text = "Can you walk me through a clear code or practical scenario showing how you would apply that in a real project?"
                concepts = "practical scenario, implementation steps, real-world use case, expected output"
            else:
                intermediate_topics = [
                    ("What is the difference between a List and a Set, and in what situation would you prefer a Set?", "unique elements, duplicates allowed, ordering, lookup performance, hash set"),
                    ("How does error handling work with try, catch, and finally blocks in programming?", "exception handling, runtime errors, cleanup in finally, graceful degradation"),
                    ("What is a REST API, and what is the difference between an HTTP GET request and a POST request?", "stateless, client server, GET retrieves data, POST sends data, HTTP status codes"),
                ]
                picked = intermediate_topics[(index - 1) % len(intermediate_topics)]
                q_text, concepts = picked[0], picked[1]

        return {
            "question_text": q_text,
            "expected_concepts": concepts,
            "question_type": decision_type,
            "difficulty_level": difficulty,
            "order_index": index,
        }


# Singleton instance
ai_agent_service = AIAgentService()
