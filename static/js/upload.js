const form = document.getElementById("uploadForm");
const statusBox = document.getElementById("status");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusBox.hidden = false;
  statusBox.className = "status working";
  statusBox.textContent = "Uploading, transcribing audio, and aligning the score…";
  const button = form.querySelector("button");
  button.disabled = true;

  try {
    const response = await fetch("/api/upload", {method: "POST", body: new FormData(form)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed.");
    window.location.href = data.url;
  } catch (error) {
    statusBox.className = "status error";
    statusBox.textContent = error.message;
    button.disabled = false;
  }
});
