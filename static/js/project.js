const projectId = window.KEYFRAME_PROJECT_ID;

const video = document.getElementById("performanceVideo");
const selectedMeasure = document.getElementById("selectedMeasure");
const replayButton = document.getElementById("replayButton");
const loopToggle = document.getElementById("loopToggle");
const measureFallback = document.getElementById("measureFallback");
const overlay = document.getElementById("measureOverlay");
const scoreWrapper = document.getElementById("scoreWrapper");
const alignmentSummary = document.getElementById("alignmentSummary");

let project = null;
let activeMeasure = null;
let activeOverlay = null;

function formatTime(ms) {
  return `${(ms / 1000).toFixed(1)}s`;
}

function chooseMeasure(measure, element = null) {
  activeMeasure = measure;

  if (activeOverlay) {
    activeOverlay.classList.remove("active");
  }

  if (element) {
    element.classList.add("active");
    activeOverlay = element;
  }

  document.querySelectorAll(".measure-chip").forEach((chip) => {
    chip.classList.toggle(
      "active",
      Number(chip.dataset.measureIndex) === measure.index
    );
  });

  selectedMeasure.textContent =
    `Measure ${measure.number} · ${formatTime(measure.start_ms)}–${formatTime(measure.end_ms)}`;

  replayButton.disabled = false;
  playMeasure(measure);
}

function playMeasure(measure) {
  video.muted = false;
  if (video.volume === 0) {
    video.volume = 1.0;
  }

  video.currentTime = measure.start_ms / 1000;

  const playPromise = video.play();
  if (playPromise) {
    playPromise.catch((error) => {
      console.error("Video playback failed:", error);
    });
  }
}

video.addEventListener("timeupdate", () => {
  if (!activeMeasure) return;

  const end = activeMeasure.end_ms / 1000;

  if (video.currentTime >= end) {
    if (loopToggle.checked) {
      video.currentTime = activeMeasure.start_ms / 1000;
      video.play();
    } else {
      video.pause();
    }
  }
});

replayButton.addEventListener("click", () => {
  if (activeMeasure) {
    playMeasure(activeMeasure);
  }
});

function buildFallbackButtons() {
  measureFallback.innerHTML = "";

  project.measures.forEach((measure) => {
    const button = document.createElement("button");
    button.className = "measure-chip";
    button.dataset.measureIndex = measure.index;
    button.textContent = `M${measure.number}`;

    if (measure.inferred) {
      button.title = "Timing inferred from neighboring aligned measures";
      button.classList.add("inferred");
    }

    button.addEventListener("click", () => chooseMeasure(measure));
    measureFallback.appendChild(button);
  });
}

function clusterBoxes(boxes) {
  // OSMD creates one vf-measure box per staff.  Combine the treble/bass
  // boxes for the SAME system, but never combine boxes from different score
  // systems just because they share an x-position.
  if (!boxes.length) return [];

  const heights = boxes
    .map((box) => box.bottom - box.top)
    .filter((height) => height > 0)
    .sort((a, b) => a - b);
  const medianHeight = heights[Math.floor(heights.length / 2)] || 50;
  const maxStaffGap = Math.max(24, medianHeight * 0.8);

  const verticalGap = (a, b) => {
    if (a.bottom < b.top) return b.top - a.bottom;
    if (b.bottom < a.top) return a.top - b.bottom;
    return 0;
  };

  const clusters = [];
  const sorted = [...boxes].sort((a, b) => {
    if (Math.abs(a.top - b.top) > 8) return a.top - b.top;
    return a.x - b.x;
  });

  for (const box of sorted) {
    let cluster = clusters.find((candidate) => {
      const sameHorizontalMeasure =
        Math.abs(candidate.x - box.x) < 10 &&
        Math.abs(candidate.width - box.width) < 18;

      // This condition is the important fix: a measure in the next system
      // must not extend the hitbox vertically through the whitespace between
      // systems.
      const sameSystem = verticalGap(candidate, box) <= maxStaffGap;

      return sameHorizontalMeasure && sameSystem;
    });

    if (!cluster) {
      clusters.push({
        x: box.x,
        width: box.width,
        top: box.top,
        bottom: box.bottom,
      });
    } else {
      cluster.x = Math.min(cluster.x, box.x);
      cluster.width = Math.max(
        cluster.x + cluster.width,
        box.x + box.width
      ) - cluster.x;
      cluster.top = Math.min(cluster.top, box.top);
      cluster.bottom = Math.max(cluster.bottom, box.bottom);
    }
  }

  return clusters.sort((a, b) => {
    if (Math.abs(a.top - b.top) > maxStaffGap) return a.top - b.top;
    return a.x - b.x;
  });
}

function buildMeasureOverlays() {
  overlay.innerHTML = "";

  const wrapperRect = scoreWrapper.getBoundingClientRect();
  const groups = Array.from(document.querySelectorAll("#score svg g.vf-measure"));

  if (!groups.length) {
    // The measure-strip remains available if a future OSMD release changes DOM classes.
    return;
  }

  const boxes = groups.map((group) => {
    const rect = group.getBoundingClientRect();
    return {
      x: rect.left - wrapperRect.left,
      top: rect.top - wrapperRect.top,
      bottom: rect.bottom - wrapperRect.top,
      width: rect.width,
    };
  }).filter((box) => box.width > 15);

  const clusters = clusterBoxes(boxes).slice(0, project.measures.length);

  clusters.forEach((box, index) => {
    const measure = project.measures[index];
    if (!measure) return;

    const hit = document.createElement("button");
    hit.className = "measure-hit";
    hit.style.left = `${box.x}px`;
    hit.style.top = `${box.top}px`;
    hit.style.width = `${box.width}px`;
    hit.style.height = `${Math.max(30, box.bottom - box.top)}px`;
    hit.setAttribute("aria-label", `Play measure ${measure.number}`);

    hit.addEventListener("click", () => chooseMeasure(measure, hit));
    overlay.appendChild(hit);
  });
}

async function renderScore() {
  const osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay("score", {
    autoResize: true,
    backend: "svg",
    drawTitle: false,
    followCursor: false,
  });

  await osmd.load(project.score_url);
  await osmd.render();

  requestAnimationFrame(() => {
    buildMeasureOverlays();
  });

  window.addEventListener("resize", () => {
    clearTimeout(window.__keyframeResize);
    window.__keyframeResize = setTimeout(buildMeasureOverlays, 150);
  });
}

async function start() {
  const response = await fetch(`/api/project/${projectId}`);
  project = await response.json();

  if (!response.ok) {
    throw new Error(project.error || "Unable to load project.");
  }

  document.getElementById("projectTitle").textContent = project.title;
  video.src = project.video_url;


  const alignment = project.alignment;
  alignmentSummary.textContent =
    `${alignment.matched_onsets}/${alignment.score_onsets} score onsets aligned`;

  buildFallbackButtons();
  await renderScore();
}

start().catch((error) => {
  document.getElementById("score").innerHTML =
    `<div class="status error">${error.message}</div>`;
});
