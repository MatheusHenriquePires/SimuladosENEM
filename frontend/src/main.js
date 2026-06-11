const state = {
  currentExam: null,
  showAnswers: false,
  answers: {},
};

const mixForm = document.getElementById("mix-form");
const statusEl = document.getElementById("status");
const questionsEl = document.getElementById("questions");
const examMetaEl = document.getElementById("exam-meta");
const toggleAnswersBtn = document.getElementById("toggle-answers-btn");
const exportPdfBtn = document.getElementById("export-pdf-btn");
const generateBtn = document.getElementById("generate-btn");
const daySelect = document.getElementById("day");
const languageField = document.getElementById("language-field");

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

function getStudentId() {
  const storageKey = "enem-student-id";
  let studentId = localStorage.getItem(storageKey);

  if (!studentId) {
    studentId = crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(storageKey, studentId);
  }

  return studentId;
}

function getAnswersStorageKey(examId) {
  return `enem-answers-${examId}`;
}

function loadSavedAnswers(examId) {
  try {
    state.answers = JSON.parse(localStorage.getItem(getAnswersStorageKey(examId))) || {};
  } catch {
    state.answers = {};
  }
}

function saveAnswer(questionIndex, letter) {
  if (!state.currentExam) return;

  state.answers[String(questionIndex)] = letter;
  localStorage.setItem(
    getAnswersStorageKey(state.currentExam.id),
    JSON.stringify(state.answers)
  );
}

function renderExamMeta(exam) {
  examMetaEl.classList.remove("hidden");
  const languageMeta = exam.day === 1 ? ` - Idioma ${exam.language}` : "";
  examMetaEl.innerHTML = `
    <strong>Simulado gerado</strong> - ID: ${exam.id}<br>
    Dia ${exam.day}<br>
    Anos sorteados: ${exam.years.join(" -> ")}<br>
    Caderno ${exam.caderno}${languageMeta} - ${exam.questions.length} questoes
  `;
}

function renderQuestions(exam) {
  questionsEl.innerHTML = exam.questions
    .map((question) => {
      const savedAnswer = state.answers[String(question.mixedIndex)];
      const alternatives = question.alternatives
        .map((alt) => {
          const checked = savedAnswer === alt.letter ? "checked" : "";
          const isSelected = savedAnswer === alt.letter ? "selected" : "";
          const isCorrect = state.showAnswers && alt.isCorrect ? "correct" : "";

          return `
            <li class="${isCorrect} ${isSelected}">
              <label class="answer-option">
                <input
                  type="radio"
                  name="question-${question.mixedIndex}"
                  value="${alt.letter}"
                  data-question-index="${question.mixedIndex}"
                  ${checked}
                >
                <span><strong>${alt.letter})</strong> ${renderMarkdown(alt.text)}</span>
              </label>
            </li>
          `;
        })
        .join("");

      return `
        <article class="question-card" data-index="${question.mixedIndex}">
          <div class="question-header">
            <h3>Questao ${question.mixedIndex}</h3>
            <span class="question-origin">ENEM ${question.originalYear} - item ${question.originalIndex}</span>
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

  questionsEl.querySelectorAll('input[type="radio"]').forEach((input) => {
    input.addEventListener("change", (event) => {
      saveAnswer(event.target.dataset.questionIndex, event.target.value);
      renderQuestions(exam);
    });
  });
}

async function generateMix(event) {
  event.preventDefault();

  const language = document.getElementById("language").value;
  const day = Number(daySelect.value);

  generateBtn.disabled = true;
  setStatus("Gerando simulado unico...");

  try {
    const response = await fetch("/api/mix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ day, language, studentId: getStudentId() }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Erro ao gerar simulado.");
    }

    state.currentExam = payload;
    state.showAnswers = false;
    loadSavedAnswers(payload.id);
    renderExamMeta(payload);
    renderQuestions(payload);

    toggleAnswersBtn.disabled = false;
    toggleAnswersBtn.textContent = "Mostrar gabarito";

    exportPdfBtn.href = `/api/mix/${payload.id}/pdf`;
    exportPdfBtn.classList.remove("disabled");

    setStatus(`Simulado pronto com ${payload.questions.length} questoes.`);
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

function updateLanguageVisibility() {
  const isDayOne = Number(daySelect.value) === 1;
  languageField.classList.toggle("hidden", !isDayOne);
}

mixForm.addEventListener("submit", generateMix);
toggleAnswersBtn.addEventListener("click", toggleAnswers);
daySelect.addEventListener("change", updateLanguageVisibility);
updateLanguageVisibility();
