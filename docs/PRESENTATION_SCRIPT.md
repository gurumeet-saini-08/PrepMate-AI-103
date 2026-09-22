# 🎬 5-Minute Video & Presentation Script: PrepMate
**Chitkara University | AI-103 Group Project Presentation Guide**
*(Strictly structured to the AI-103 Evaluation Rubric)*

---

## ⏱️ Exact Video & Presentation Timing Breakdown (Total: 5 Minutes)

| Section | Timestamp | Key Focus |
| :--- | :--- | :--- |
| **1. Introduction** | 0:00 – 0:30 (30s) | Team member names, Project Title ("PrepMate"), and Target Use Case |
| **2. Problem Statement** | 0:30 – 1:00 (30s) | The gap between static practice and realistic interview communication |
| **3. AI-Driven Solution** | 1:00 – 2:00 (1m) | Azure AI Speech, Microsoft Foundry, and Adaptive AI Agent decision loops |
| **4. Technical Demonstration** | 2:00 – 4:00 (2m) | Live walkthrough: Voice answer, adaptive escalation, scorecard & Daily Coach |
| **5. Impact & Future Scope** | 4:00 – 5:00 (1m) | Measurable value, Responsible AI compliance, limitations, and future roadmap |

---

## 🎤 Verbatim Presentation Script (Word-for-Word Guide)

### 1. Introduction (0:00 – 0:30 | Speaker 1)
> *"Respected instructor and classmates, welcome. We are Team [Team Name], consisting of [Member 1, Member 2, Member 3, and Member 4].*  
> *Today, we are presenting our AI-103 project: **PrepMate — an AI-Powered Response & Communication Coach**.*  
> *Under Project Track #19 (AI Interview Coach), PrepMate is an interactive platform designed to bridge the critical gap students face when preparing for campus placements and technical software engineering interviews."*

---

### 2. Problem Statement (0:30 – 1:00 | Speaker 2)
> *"When students prepare for job interviews, they typically read static questions online or practice answering in front of a mirror. But this creates two major blind spots:*  
> *First: **'Was my answer actually technically accurate and complete?'***  
> *Second: **'How effectively did I communicate that answer?'***  
> *Most students have solid coding fundamentals, but stumble because of rapid speaking speed, excessive filler words like 'um' and 'basically', or disorganized explanations. Existing mock interview tools are just static question lists or generic chatbots that ignore verbal delivery completely. Students need realistic, dynamic practice with objective feedback on both substance and delivery."*

---

### 3. AI-Driven Solution & Architecture (1:00 – 2:00 | Speaker 3)
> *"To solve this, PrepMate integrates three core AI capabilities:*  
> *1. **Azure AI Speech Service:** Captures the candidate's spoken voice in real time via microphone, converting audio into high-accuracy transcripts while extracting verbal delivery metrics—such as Words Per Minute (WPM), hesitation pauses, and filler word frequency.*  
> *2. **Generative AI via Microsoft Foundry / Azure OpenAI:** Rather than basic keyword matching, our GenAI engine evaluates conceptual coverage, technical depth, and missing edge cases against industry standards.*  
> *3. **The Adaptive AI Agent:** This is what sets PrepMate apart. The AI Agent acts as an active decision maker. If a candidate provides a high-scoring answer with fluent delivery, the agent **escalates** difficulty into architectural internals. If a candidate struggles, the agent **simplifies**, pivoting to a guided real-world analogy to scaffold understanding.*  
> *Everything is orchestrated via a clean Python Flask backend with an SQLite relational store."*

---

### 4. Technical Demonstration (2:00 – 4:00 | Speaker 4 / Live Demo)
*(Screen Recording / Live Walkthrough)*

> 1. **Dashboard & Setup (2:00 – 2:30):**  
> *"Here is the student dashboard. We select our target role as 'Software Developer' with an Intermediate difficulty and launch the interview room.*  
> *Notice that this does not look like a chatbot—it is designed like an authentic interview room."*

> 2. **AI Question & Spoken Answer (2:30 – 3:15):**  
> *"The AI interviewer asks: 'Explain polymorphism in Java and runtime dispatch.'*  
> *We click the microphone and answer using natural speech: [Candidate speaks answer].*  
> *Observe the live waveform visualizer and speech recognition tracking words in real time. We purposely included a couple of filler words—'um' and 'basically'—to test our communication detector."*

> 3. **Adaptive Agent Decision & Next Question (3:15 – 3:35):**  
> *"Upon submission, our dual evaluation kicks in immediately. The AI Agent notes high technical correctness and crisp delivery, so notice the badge: the agent automatically **escalates** to an advanced question on virtual method tables (vtables)!"*

> 4. **Performance Report & Daily Coach (3:35 – 4:00):**  
> *"Upon concluding the interview, PrepMate generates this comprehensive Performance Report:*  
> *- Response Correctness: 85%*  
> *- Communication Delivery: 78%*  
> *- Detailed metrics: 132 WPM, 2 filler words detected, along with exact missing concepts and model answers.*  
> *Back on the dashboard, our unique **Daily Coach** feature has updated with a personalized 60-second micro-drill targeting our specific weakness."*

---

### 5. Impact, Responsible AI & Future Scope (4:00 – 5:00 | Speaker 1 / Team)
> *"**Practical Impact:** PrepMate transforms passive reading into active, high-retention interview simulation, directly boosting campus placement readiness.*  
> *Regarding **Responsible AI**, PrepMate adheres strictly to Microsoft's Six Ethical Principles: candidate audio is never stored permanently, scores are transparently itemized with explainable feedback, and our dual-mode input toggle ensures accessibility for diverse acoustic environments.*  
> *For **Future Scope**, we aim to explore multimodal feedback—analyzing camera-based eye contact and experimenting with voice prosody indicators.*  
> *Thank you, and we welcome your questions!"*

---

## 🎯 Answers to the 4 Core Class Presentation Questions (Page 3 of Guidelines)

### 1. What problem did we solve?
We solved the lack of objective, personalized feedback in technical interview preparation by uniting **technical accuracy evaluation** with **spoken communication analysis** in an adaptive mock environment.

### 2. What did we build?
We built **PrepMate**, an AI-powered interview preparation web platform featuring a realistic virtual interview room, real-time speech transcription, dual-dimension scoring, an adaptive AI interview agent, and a personalized Daily Coach.

### 3. How did we apply our AI-103 learning?
We applied:
- **Azure AI Speech Services** for live Speech-to-Text (STT) and question vocalization (TTS).
- **Microsoft Foundry / Azure OpenAI** for Generative AI evaluation and question synthesis.
- **AI Agent Workflow Pattern** to dynamically control interview progression (escalation vs. scaffolding) based on candidate performance.
- **Responsible AI Principles** covering data privacy, explainability, accessibility, and ethical AI scoring.

### 4. Can we demonstrate that it works?
**Yes, 100% live end-to-end.** The application runs locally on `http://127.0.0.1:5000` with dual-mode capability (Azure cloud services + resilient intelligent fallback), passing all automated test suites and live voice trials.
