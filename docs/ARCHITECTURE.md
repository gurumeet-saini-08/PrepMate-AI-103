# 🏛️ PrepMate Architecture & System Design
**Chitkara University | AI-103 Group Project Documentation**

---

## 1. High-Level System Architecture

PrepMate follows a modular multi-tier architecture uniting speech processing, generative intelligence, agent decision orchestration, and relational persistence.

```mermaid
flowchart TD
    subgraph Client["Frontend Client (HTML5 / CSS3 / Vanilla JS)"]
        UI["Interview Room UI"]
        Mic["Browser Microphone / Web Audio API"]
        Wave["HTML5 Canvas Waveform Visualizer"]
        HUD["Live Metrics HUD (WPM, Fillers, Timer)"]
    end

    subgraph Flask["Flask Application Tier (Python 3.12)"]
        Routes["Blueprint Routes (Auth, Profile, Interview, API)"]
        SpeechSvc["SpeechService (Azure AI Speech)"]
        CommSvc["CommunicationService (WPM, Fillers, Structure)"]
        AgentSvc["AIAgentService (Adaptive State Orchestrator)"]
        CoachSvc["CoachService (Daily Micro-Drills)"]
    end

    subgraph CloudAI["Microsoft Azure AI Services"]
        AzureSTT["Azure AI Speech (STT & TTS)"]
        Foundry["Microsoft Foundry / Azure OpenAI (gpt-5-mini)"]
    end

    subgraph DB["Relational Storage (SQLite + SQLAlchemy)"]
        Users[("Users & Profiles")]
        Sessions[("Interview Sessions")]
        QA[("Questions & Responses")]
        CommData[("Communication Analyses")]
    end

    Mic -->|Audio Stream| Wave
    Mic -->|Audio Blob / Web Speech| Routes
    Routes --> SpeechSvc
    SpeechSvc --> AzureSTT
    Routes --> CommSvc
    Routes --> AgentSvc
    AgentSvc --> Foundry
    AgentSvc --> CommSvc
    Routes --> DB
    AgentSvc -->|Adaptive Decision| UI
    CoachSvc --> DB
```

---

## 2. The Adaptive AI Agent Decision Loop

Rather than displaying a static predetermined questionnaire, PrepMate employs an **AI Agent state machine** that evaluates both candidate knowledge and vocal delivery to choose the optimal next step:

```mermaid
flowchart TD
    Start([Start Interview]) --> Q1[Generate Initial Question]
    Q1 --> Answer[Student Speaks Answer via Microphone]
    Answer --> STT[Azure AI Speech STT Transcription]
    STT --> Eval[Dual Dimension Analysis]

    subgraph DualEval [Evaluation Engine]
        Eval --> Correctness[GenAI Technical Correctness 0-10]
        Eval --> Communication[Delivery Metrics: WPM, Fillers, Pauses]
    end

    Correctness & Communication --> Decision{AI Agent Decision}

    Decision -->|Correctness >= 8.0 & Comm >= 7.0| Escalate[Escalate: Advanced Internal Mechanics / Edge Cases]
    Decision -->|Correctness <= 5.0| Simplify[Simplify: Guided Real-World Analogy]
    Decision -->|Fillers >= 4 or Comm < 6.0| Structure[Follow-Up: Concrete Code Walkthrough]
    Decision -->|Standard Passing| NextCore[Progress: Next Curriculum Topic]

    Escalate & Simplify & Structure & NextCore --> LimitCheck{Question Limit Reached?}
    LimitCheck -->|No| Answer
    LimitCheck -->|Yes| Report[Generate Final Scorecard & Daily Coach]
    Report --> End([Interview Completed])
```

---

## 3. Communication Analysis Pipeline

The communication analyzer (`services/communication_service.py`) calculates speech delivery metrics:

1. **Speaking Rate (WPM):**
   $$\text{WPM} = \frac{\text{Spoken Word Count}}{\text{Elapsed Duration in Seconds} / 60}$$
   - *Target Professional Range:* 120 – 150 Words Per Minute.
2. **Filler Word Scanner:**
   - Evaluates regular expressions for speech hesitation tokens: `um`, `umm`, `uh`, `like`, `basically`, `actually`, `you know`, `literally`, `sort of`, `kind of`.
   - Returns itemized frequency dictionary for actionable coaching.
3. **Fluency Rating:**
   - Categorized as `Excellent`, `Good`, `Moderate`, or `Needs Improvement` based on filler ratio and WPM stability.
4. **Answer Structure Scoring:**
   - Detects linguistic anchors for **Definition/Premise**, **Explanation Mechanism**, **Example/Application**, and **Conclusion/Synthesis**.
