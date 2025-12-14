const API = "http://localhost:8000";
let currentJobId = null;

async function createJob() {
  const file = document.getElementById("fileInput").files[0];
  const episodeName = document.getElementById("episodeName").value;

  if (!file || !episodeName) {
    alert("Missing file or episode name");
    return;
  }

  const form = new FormData();
  form.append("file", file);
  form.append("episode_name", episodeName);

  const res = await fetch(`${API}/jobs`, {
    method: "POST",
    body: form,
  });

  const data = await res.json();
  currentJobId = data.job_id;
  document.getElementById("jobId").innerText = currentJobId;
}

async function runAnalysis() {
  if (!currentJobId) return alert("No job");

  await fetch(`${API}/jobs/${currentJobId}/manual`, {
    method: "POST",
  });

  alert("Analysis triggered");
}

async function getAnalysis() {
  if (!currentJobId) return alert("No job");

  const res = await fetch(`${API}/jobs/${currentJobId}/analysis`);
  const data = await res.json();

  document.getElementById("analysisOutput").innerText =
    JSON.stringify(data, null, 2);
}

async function exportDeck() {
  if (!currentJobId) return alert("No job");

  const payload = {
    job_id: currentJobId,
    source_lang_tag: "SV",
    target_lang_tag: "EN-GB",
    deck_name: "Persdeck Export",
    export_options: {
      include_sentence: true
    }
  };

  const res = await fetch(`${API}/jobs/${currentJobId}/deck`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "quizlet.tsv";
  a.click();

  window.URL.revokeObjectURL(url);
}
