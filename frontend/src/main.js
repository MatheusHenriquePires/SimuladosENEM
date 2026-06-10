const state = {
  years: [],
  currentExam: null,
  showAnswers: false,
};

const yearsList = document.getElementById("years-list");
const mixForm = document.getElementById("mix-form");
const statusEl = document.getElementById("status");
const questionsEl = document.getElementById("questions");
const examMetaEl = document.getElementById("exam-meta");
const toggleAnswersBtn = document.getElementById("toggle-answers-btn");
const exportPdfBtn = document.getElementById("export-pdf-btn");
const generateBtn = document.getElementById("generate-btn");

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function renderMarkdown(text) {
  if (!text) return "";

  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img alt="$1" src="$2">');
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(/\n/g, "<br>");
  return html;
}

function getSelectedYears() {
  return [...yearsList.querySelectorAll("input:checked")].map(
    (input) => Number(input.value)
  );
}

function renderYears() {
  yearsList.innerHTML = state.years
    .map(
      (year) => `
      <label class="year-chip">
        <input type="checkbox" name="year" value="${year}">
        <span>${year}</span>
      </label>
    `
    )
    .join("");

  yearsList.querySelectorAll(".year-chip").forEach((chip) => {
    const input = chip.querySelector("input");
    input.addEventListener("change", () => {
      chip.classList.toggle("selected", input.checked);
    });
  });

  const defaults = state.years.slice(0, 3);
  yearsList.querySelectorAll("input").forEach((input) => {
    if (defaults.includes(Number(input.value))) {
      input.checked = true;
      input.closest(".year-chip").classList.add("selected");
    }
  });
}

function renderExamMeta(exam) {
  examMetaEl.classList.remove("hidden");
  examMetaEl.innerHTML = `
    <strong>Simulado gerado</strong> — ID: ${exam.id}<br>
    Rotação: ${exam.years.join(" → ")} (repetindo)<br>
    Caderno ${exam.caderno} · Idioma ${exam.language} · ${exam.questions.length} questões
  `;
}

function renderQuestions(exam) {
  questionsEl.innerHTML = exam.questions
    .map((question) => {
      const alternatives = question.alternatives
        .map(
          (alt) => `
          <li class="${state.showAnswers && alt.isCorrect ? "correct" : ""}">
            <strong>${alt.letter})</strong> ${alt.text}
          </li>
        `
        )
        .join("");

      return `
        <article class="question-card" data-index="${question.mixedIndex}">
          <div class="question-header">
            <h3>Questão ${question.mixedIndex}</h3>
            <span class="question-origin">ENEM ${question.originalYear} · item ${question.originalIndex}</span>
          </div>
          <div class="context">${renderMarkdown(question.context)}</div>
          ${
            question.alternativesIntroduction
              ? `<div class="intro">${renderMarkdown(question.alternativesIntroduction)}</div>`
              : ""
          }
          <ul class="alternatives">${alternatives}</ul>
          <span class="answer-badge ${state.showAnswers ? "" : "hidden"}">
            Gabarito: ${question.correctAlternative}
          </span>
        </article>
      `;
    })
    .join("");
}

async function loadYears() {
  const response = await fetch("/api/years");
  if (!response.ok) {
    throw new Error("Não foi possível carregar os anos disponíveis.");
  }
  const data = await response.json();
  state.years = data.years;
  renderYears();
}

async function generateMix(event) {
  event.preventDefault();

  const years = getSelectedYears();
  const caderno = document.getElementById("caderno").value;
  const language = document.getElementById("language").value;

  if (years.length < 2) {
    setStatus("Selecione pelo menos 2 anos.", true);
    return;
  }

  generateBtn.disabled = true;
  setStatus("Gerando simulado... isso pode levar alguns segundos na primeira vez.");

  try {
    const response = await fetch("/api/mix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ years, caderno, language }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Erro ao gerar simulado.");
    }

    state.currentExam = payload;
    state.showAnswers = false;
    renderExamMeta(payload);
    renderQuestions(payload);

    toggleAnswersBtn.disabled = false;
    toggleAnswersBtn.textContent = "Mostrar gabarito";

    exportPdfBtn.href = `/api/mix/${payload.id}/pdf`;
    exportPdfBtn.classList.remove("disabled");

    setStatus(`Simulado pronto com ${payload.questions.length} questões.`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    generateBtn.disabled = false;
  }
}

function toggleAnswers() {
  if (!state.currentExam) return;
  state.showAnswers = !state.showAnswers;
  toggleAnswersBtn.textContent = state.showAnswers
    ? "Ocultar gabarito"
    : "Mostrar gabarito";
  renderQuestions(state.currentExam);
}

mixForm.addEventListener("submit", generateMix);
toggleAnswersBtn.addEventListener("click", toggleAnswers);

loadYears().catch((error) => setStatus(error.message, true));
