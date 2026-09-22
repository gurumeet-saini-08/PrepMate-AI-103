// PrepMate Main JS
document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash alerts
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = "opacity 0.5s ease";
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 500);
    }, 4500);
  });

  // Query live status
  fetch("/api/system-status")
    .then((r) => r.json())
    .then((data) => {
      const pill = document.getElementById("navStatusPill");
      const dot = document.getElementById("navStatusDot");
      const text = document.getElementById("navStatusText");
      if (pill && dot && text) {
        text.innerText = data.mode;
        if (data.mode === "Azure Live") {
          dot.className = "status-dot";
          pill.title = "Connected to Azure AI Speech & Microsoft Foundry";
        } else if (data.mode === "Hybrid Azure") {
          dot.className = "status-dot";
          pill.title = "Connected to Azure Service";
        } else {
          dot.className = "status-dot fallback";
          pill.title = "Operating in Local Intelligent Fallback Mode (No Azure keys loaded)";
        }
      }
    })
    .catch((err) => console.log("System status check:", err));

  // Mobile Navigation Drawer Toggle
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");

  if (navToggle && navLinks) {
    navToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = navLinks.classList.toggle("nav-active");
      navToggle.classList.toggle("active", isOpen);
      navToggle.setAttribute("aria-expanded", isOpen);
    });

    // Close mobile menu when clicking outside
    document.addEventListener("click", (e) => {
      if (navLinks.classList.contains("nav-active") && !navLinks.contains(e.target) && !navToggle.contains(e.target)) {
        navLinks.classList.remove("nav-active");
        navToggle.classList.remove("active");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });

    // Close mobile menu when any nav link is tapped
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        navLinks.classList.remove("nav-active");
        navToggle.classList.remove("active");
        navToggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  // Interactive Cursor Effects (Ambient Glow, Cursor Dot, Micro-Sparkles, Click Wave, 3D Tilt)
  const isTouchDevice = window.matchMedia("(pointer: coarse)").matches || window.innerWidth <= 768;
  const cursorGlow = document.getElementById("cursorGlow");
  const cursorDot = document.getElementById("cursorDot");

  if (!isTouchDevice && cursorGlow && cursorDot) {
    let mouseX = -500;
    let mouseY = -500;
    let glowX = -500;
    let glowY = -500;
    let isVisible = false;
    let lastSparkleTime = 0;

    // Smooth animation loop for ambient glow lag & dot follow
    function renderCursor() {
      // Linear interpolation (lerp) for smooth trailing glow
      glowX += (mouseX - glowX) * 0.12;
      glowY += (mouseY - glowY) * 0.12;

      cursorGlow.style.left = `${glowX}px`;
      cursorGlow.style.top = `${glowY}px`;

      cursorDot.style.left = `${mouseX}px`;
      cursorDot.style.top = `${mouseY}px`;

      requestAnimationFrame(renderCursor);
    }
    requestAnimationFrame(renderCursor);

    // Track mouse movement
    document.addEventListener("mousemove", (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;

      if (!isVisible) {
        isVisible = true;
        cursorGlow.style.opacity = "1";
        cursorDot.style.opacity = "1";
      }

      // Micro-sparkle particle trail (throttled)
      const now = Date.now();
      if (now - lastSparkleTime > 80) {
        lastSparkleTime = now;
        createSparkle(e.clientX, e.clientY);
      }
    });

    // Fade out when cursor leaves document window
    document.addEventListener("mouseleave", () => {
      isVisible = false;
      cursorGlow.style.opacity = "0";
      cursorDot.style.opacity = "0";
    });

    // Expand glow and magnify dot when hovering interactive elements
    const interactiveSelector = "a, button, .btn, input, select, textarea, .card, .hero-visual, .badge";
    document.addEventListener("mouseover", (e) => {
      if (e.target && e.target.closest && e.target.closest(interactiveSelector)) {
        cursorGlow.classList.add("active");
        cursorDot.classList.add("active");
      }
    });

    document.addEventListener("mouseout", (e) => {
      if (e.target && e.target.closest && e.target.closest(interactiveSelector)) {
        cursorGlow.classList.remove("active");
        cursorDot.classList.remove("active");
      }
    });

    // Click Ripple Wave Effect
    document.addEventListener("click", (e) => {
      createRipple(e.clientX, e.clientY);
    });

    // Sparkle generator helper
    function createSparkle(x, y) {
      const sparkle = document.createElement("div");
      sparkle.className = "cursor-sparkle";
      const size = Math.random() * 4 + 3; // 3px to 7px
      sparkle.style.width = `${size}px`;
      sparkle.style.height = `${size}px`;
      sparkle.style.left = `${x}px`;
      sparkle.style.top = `${y}px`;

      // Random slight drift
      const dx = (Math.random() - 0.5) * 36;
      const dy = (Math.random() - 0.5) * 36;
      sparkle.style.setProperty("--dx", `${dx}px`);
      sparkle.style.setProperty("--dy", `${dy}px`);

      document.body.appendChild(sparkle);
      setTimeout(() => sparkle.remove(), 650);
    }

    // Ripple wave generator helper
    function createRipple(x, y) {
      const ripple = document.createElement("div");
      ripple.className = "cursor-ripple";
      ripple.style.left = `${x}px`;
      ripple.style.top = `${y}px`;
      document.body.appendChild(ripple);
      setTimeout(() => ripple.remove(), 550);
    }
  }

  // 3D Card Tilt Effect for Hero Visual Card
  const heroVisual = document.getElementById("heroVisual");
  if (heroVisual && !window.matchMedia("(pointer: coarse)").matches) {
    heroVisual.addEventListener("mousemove", (e) => {
      const rect = heroVisual.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      // Calculate tilt angles (subtle: max ~7 degrees)
      const rotateX = ((centerY - y) / centerY) * 7;
      const rotateY = ((x - centerX) / centerX) * 7;

      heroVisual.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px) scale3d(1.02, 1.02, 1.02)`;
    });

    heroVisual.addEventListener("mouseleave", () => {
      heroVisual.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)";
    });
  }
});
