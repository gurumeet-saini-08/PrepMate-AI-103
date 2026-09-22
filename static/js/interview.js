// PrepMate Realistic Interview Room Engine
document.addEventListener("DOMContentLoaded", () => {
  const recordBtn = document.getElementById("recordBtn");
  const stopBtn = document.getElementById("stopBtn");
  const submitBtn = document.getElementById("submitBtn");
  const audioPlayBtn = document.getElementById("playQuestionBtn");
  const transcriptBox = document.getElementById("liveTranscript");
  const manualTextInput = document.getElementById("manualAnswerText");

  const timerDisplay = document.getElementById("timerDisplay");
  const wpmDisplay = document.getElementById("wpmDisplay");
  const fillerDisplay = document.getElementById("fillerDisplay");
  const canvas = document.getElementById("waveformCanvas");

  const voiceTabBtn = document.getElementById("voiceTabBtn");
  const textTabBtn = document.getElementById("textTabBtn");
  const voiceStudio = document.getElementById("voiceStudio");
  const textStudio = document.getElementById("textStudio");

  let mediaRecorder = null;
  let audioChunks = [];
  let audioStream = null;
  let audioContext = null;
  let analyser = null;
  let animationId = null;

  let isRecording = false;
  let startTime = null;
  let timerInterval = null;
  let elapsedSeconds = 0;

  let speechRecognition = null;
  let accumulatedTranscript = "";

  const FILLER_WORDS = ["um", "umm", "uh", "er", "ah", "like", "basically", "actually", "literally", "you know"];

  // Tab switching
  if (voiceTabBtn && textTabBtn) {
    voiceTabBtn.addEventListener("click", () => {
      voiceTabBtn.classList.add("active");
      textTabBtn.classList.remove("active");
      voiceStudio.style.display = "block";
      textStudio.style.display = "none";
    });

    textTabBtn.addEventListener("click", () => {
      textTabBtn.classList.add("active");
      voiceTabBtn.classList.remove("active");
      voiceStudio.style.display = "none";
      textStudio.style.display = "block";
      if (isRecording) stopRecording();
    });
  }

  // Audio Playback for AI Interviewer Question (Azure TTS with Browser Fallback)
  if (audioPlayBtn) {
    audioPlayBtn.addEventListener("click", async () => {
      const qTextElement = document.getElementById("questionContent");
      if (!qTextElement) return;
      const qText = qTextElement.innerText.trim();
      const originalHtml = audioPlayBtn.innerHTML;
      audioPlayBtn.disabled = true;
      audioPlayBtn.innerHTML = "🔊 Generating Azure TTS...";

      try {
        const response = await fetch("/api/synthesize-speech", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: qText }),
        });
        const data = await response.json();
        if (data.success && data.audio_url) {
          const audio = new Audio(data.audio_url);
          audioPlayBtn.innerHTML = "🔊 Playing Azure TTS...";
          audio.play();
          audio.onended = () => {
            audioPlayBtn.disabled = false;
            audioPlayBtn.innerHTML = originalHtml;
          };
          audio.onerror = () => {
            fallbackBrowserTTS(qText, originalHtml);
          };
          return;
        }
      } catch (err) {
        console.warn("Azure TTS API unavailable, falling back to Browser TTS:", err);
      }

      fallbackBrowserTTS(qText, originalHtml);
    });
  }

  function fallbackBrowserTTS(text, originalHtml) {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      audioPlayBtn.innerHTML = "🔊 Speaking...";
      utterance.onend = () => {
        audioPlayBtn.disabled = false;
        audioPlayBtn.innerHTML = originalHtml;
      };
      utterance.onerror = () => {
        audioPlayBtn.disabled = false;
        audioPlayBtn.innerHTML = originalHtml;
      };
      window.speechSynthesis.speak(utterance);
    } else {
      audioPlayBtn.disabled = false;
      audioPlayBtn.innerHTML = originalHtml;
    }
  }

  // Web Speech API Initialization for live on-screen transcript
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRec) {
    speechRecognition = new SpeechRec();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = "en-US";

    speechRecognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = 0; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript + " ";
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      accumulatedTranscript = (final + interim).trim();
      updateTranscriptUI(accumulatedTranscript);
      updateLiveMetrics(accumulatedTranscript);
    };

    speechRecognition.onerror = (err) => {
      console.warn("SpeechRecognition event warning:", err.error);
    };
  }

  function updateTranscriptUI(text) {
    if (!transcriptBox) return;
    if (text) {
      transcriptBox.classList.remove("empty");
      transcriptBox.innerText = text;
    } else {
      transcriptBox.classList.add("empty");
      transcriptBox.innerText = "Listening... Speak clearly into your microphone.";
    }
    if (manualTextInput) {
      manualTextInput.value = text;
    }
  }

  function updateLiveMetrics(text) {
    const words = text.trim().split(/\s+/).filter(Boolean);
    const wordCount = words.length;

    // Calculate live WPM
    const minutes = Math.max(0.08, elapsedSeconds / 60);
    const liveWpm = Math.round(wordCount / minutes);
    if (wpmDisplay) wpmDisplay.innerText = wordCount > 0 ? liveWpm : "0";

    // Count fillers
    let liveFillers = 0;
    words.forEach((w) => {
      const cleaned = w.toLowerCase().replace(/[^a-z]/g, "");
      if (FILLER_WORDS.includes(cleaned)) {
        liveFillers++;
      }
    });
    if (fillerDisplay) fillerDisplay.innerText = liveFillers;
  }

  // Start Recording
  async function startRecording() {
    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];

      mediaRecorder = new MediaRecorder(audioStream);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      // When recording stops, send audio to Azure Speech STT Endpoint
      mediaRecorder.onstop = async () => {
        if (audioChunks.length > 0) {
          const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.wav");

          try {
            if (transcriptBox && !accumulatedTranscript) {
              transcriptBox.innerText = "Transcribing with Azure AI Speech...";
            }
            const resp = await fetch("/api/transcribe-audio", {
              method: "POST",
              body: formData,
            });
            const res = await resp.json();
            if (res.success && res.text) {
              accumulatedTranscript = res.text;
              updateTranscriptUI(res.text);
              updateLiveMetrics(res.text);
            } else if (accumulatedTranscript) {
              updateTranscriptUI(accumulatedTranscript);
            }
          } catch (e) {
            console.warn("Azure STT transcription request failed:", e);
            if (accumulatedTranscript) updateTranscriptUI(accumulatedTranscript);
          }
        }
      };

      mediaRecorder.start(250);

      // Start Web Speech recognition
      if (speechRecognition) {
        accumulatedTranscript = "";
        try {
          speechRecognition.start();
        } catch (e) {
          console.log("SpeechRec already running");
        }
      }

      // Initialize HTML5 Canvas Visualizer
      setupAudioVisualizer(audioStream);

      // UI state
      isRecording = true;
      recordBtn.classList.add("recording");
      recordBtn.innerHTML = "⏹️";
      recordBtn.title = "Click to pause/stop";
      if (stopBtn) stopBtn.disabled = false;
      if (submitBtn) submitBtn.disabled = true;

      elapsedSeconds = 0;
      updateTranscriptUI("");
      startTime = Date.now();
      timerInterval = setInterval(updateTimer, 1000);
    } catch (err) {
      alert("Microphone access denied or not available. Please allow microphone permissions or switch to the Text Answer tab.");
      console.error("Microphone error:", err);
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;

    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    if (audioStream) {
      audioStream.getTracks().forEach((track) => track.stop());
    }
    if (speechRecognition) {
      try {
        speechRecognition.stop();
      } catch (e) {}
    }
    if (timerInterval) clearInterval(timerInterval);
    if (animationId) cancelAnimationFrame(animationId);

    // Reset visualizer canvas
    clearCanvas();

    recordBtn.classList.remove("recording");
    recordBtn.innerHTML = "🎤";
    recordBtn.title = "Click to record";
    if (submitBtn) submitBtn.disabled = false;
  }

  function updateTimer() {
    elapsedSeconds++;
    const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
    const secs = String(elapsedSeconds % 60).padStart(2, "0");
    if (timerDisplay) timerDisplay.innerText = `${mins}:${secs}`;
    if (accumulatedTranscript) updateLiveMetrics(accumulatedTranscript);
  }

  function setupAudioVisualizer(stream) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    analyser.fftSize = 64;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
      animationId = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 1.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * (canvas.height * 0.85);

        // Modern cyan-indigo gradient
        const gradient = ctx.createLinearGradient(0, canvas.height - barHeight, 0, canvas.height);
        gradient.addColorStop(0, "#06b6d4");
        gradient.addColorStop(1, "#4f46e5");

        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

        x += barWidth + 2;
      }
    }
    draw();
  }

  function clearCanvas() {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  // Record Button Click Handler
  if (recordBtn) {
    recordBtn.addEventListener("click", () => {
      if (!isRecording) {
        startRecording();
      } else {
        stopRecording();
      }
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener("click", stopRecording);
  }

  // Submit Answer to Flask Backend
  if (submitBtn) {
    submitBtn.addEventListener("click", async () => {
      if (isRecording) stopRecording();

      // Retrieve final transcript
      let finalTranscript = accumulatedTranscript.trim();
      if (manualTextInput && (!finalTranscript || textStudio.style.display !== "none")) {
        if (manualTextInput.value.trim()) {
          finalTranscript = manualTextInput.value.trim();
        }
      }

      if (!finalTranscript) {
        alert("Please record or type an answer before submitting.");
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = "⏳ AI Evaluating Response...";

      const sessionId = document.getElementById("interviewSessionId").value;
      const questionId = document.getElementById("currentQuestionId").value;

      try {
        const response = await fetch(`/interview/${sessionId}/submit-answer`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transcript: finalTranscript,
            duration: Math.max(8.0, elapsedSeconds),
            question_id: questionId,
          }),
        });

        const result = await response.json();

        // ── Responsible AI: Handle Moderation Strike Responses ────────────────
        if (result.status === "warning") {
          // Strike 1: Show warning modal – user can re-answer
          showModerationModal("⚠️ Policy Warning", result.message, "#f59e0b", false);
          submitBtn.disabled = false;
          submitBtn.innerHTML = "🚀 Submit Answer & Next Question";
          return;
        }

        if (result.status === "locked") {
          // Strike 2: Account locked – redirect to login after dismissal
          showModerationModal("🔒 Account Suspended", result.message, "#ef4444", true);
          return;
        }

        if (result.status === "banned") {
          // Strike 3: Permanent ban – redirect to login after dismissal
          showModerationModal("🚫 Account Terminated", result.message, "#7f1d1d", true);
          return;
        }

        if (result.status === "completed") {
          window.location.href = result.redirect_url;
        } else if (result.status === "continue") {
          // Show quick alert and navigate to next question
          window.location.href = result.next_url;
        } else {
          alert("Error submitting answer: " + (result.error || "Unknown error"));
          submitBtn.disabled = false;
          submitBtn.innerHTML = "🚀 Submit Answer";
        }
      } catch (err) {
        console.error("Submission failed:", err);
        alert("Failed to submit response. Please try again.");
        submitBtn.disabled = false;
        submitBtn.innerHTML = "🚀 Submit Answer";
      }
    });
  }

  // ── Moderation Modal ────────────────────────────────────────────────────────
  function showModerationModal(title, message, color, redirect) {
    // Remove existing modal if any
    const existing = document.getElementById('moderationModal');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'moderationModal';
    overlay.style.cssText = `
      position:fixed; top:0; left:0; width:100%; height:100%;
      background:rgba(0,0,0,0.6); z-index:99999;
      display:flex; align-items:center; justify-content:center;
    `;

    overlay.innerHTML = `
      <div style="background:#fff; border-radius:12px; padding:2rem; max-width:480px; width:90%;
                  box-shadow:0 25px 50px rgba(0,0,0,0.3); border-top:5px solid ${color};">
        <h3 style="color:${color}; margin-bottom:0.75rem;">${title}</h3>
        <p style="color:#374151; font-size:0.92rem; line-height:1.6; margin-bottom:1.5rem;">${message}</p>
        <div style="display:flex; justify-content:flex-end;">
          <button id="modOkBtn" style="
            background:${color}; color:#fff; border:none; border-radius:6px;
            padding:0.65rem 1.5rem; font-size:0.95rem; font-weight:600; cursor:pointer;">
            I Understand
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById('modOkBtn').addEventListener('click', () => {
      overlay.remove();
      if (redirect) {
        window.location.href = '/logout';
      }
    });
  }
});
