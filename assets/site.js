(() => {
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navLinks = document.querySelector("[data-nav-links]");

  if (navToggle && navLinks) {
    const closeNavigation = (restoreFocus = false) => {
      const wasOpen = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", "false");
      navLinks.removeAttribute("data-open");
      const label = navToggle.querySelector(".sr-only");
      if (label) label.textContent = "Open navigation";
      if (restoreFocus && wasOpen) navToggle.focus();
    };

    navToggle.addEventListener("click", () => {
      const willOpen = navToggle.getAttribute("aria-expanded") !== "true";
      navToggle.setAttribute("aria-expanded", String(willOpen));
      if (willOpen) {
        navLinks.setAttribute("data-open", "true");
      } else {
        navLinks.removeAttribute("data-open");
      }
      const label = navToggle.querySelector(".sr-only");
      if (label) label.textContent = willOpen ? "Close navigation" : "Open navigation";
    });

    navLinks.addEventListener("click", (event) => {
      if (event.target.closest("a")) closeNavigation();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeNavigation(true);
    });
  }

  const video = document.querySelector("[data-hero-video]");
  const videoToggle = document.querySelector("[data-video-toggle]");
  const videoLabel = document.querySelector("[data-video-label]");

  if (video && videoToggle && videoLabel) {
    const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
    let userPaused = false;

    const setPausedState = (isPaused) => {
      videoToggle.setAttribute("data-paused", String(isPaused));
      videoLabel.textContent = isPaused ? "Play motion" : "Pause motion";
    };

    const playVideo = () => {
      video.play()
        .then(() => setPausedState(false))
        .catch(() => setPausedState(true));
    };

    const applyMotionPreference = () => {
      if (motionPreference.matches || userPaused) {
        video.pause();
        setPausedState(true);
      } else {
        playVideo();
      }
    };

    applyMotionPreference();
    motionPreference.addEventListener?.("change", applyMotionPreference);
    video.addEventListener("play", () => setPausedState(false));
    video.addEventListener("pause", () => setPausedState(true));

    videoToggle.addEventListener("click", () => {
      if (video.paused) {
        userPaused = false;
        playVideo();
      } else {
        userPaused = true;
        video.pause();
        setPausedState(true);
      }
    });
  }
})();
