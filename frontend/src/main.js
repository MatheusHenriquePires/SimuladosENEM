// ─── Estado Global ────────────────────────────────────────────────────────────
const state = {
  currentExam: null,
  showAnswers: false,
  answers: {},
  examFinished: false,
  result: null,
};

// ─── Elementos DOM ────────────────────────────────────────────────────────────
const mainMenu         = document.getElementById("main-menu");
const enemPanel        = document.getElementById("enem-generator-panel");
const btnMenuEnem      = document.getElementById("btn-menu-enem");
const btnBackMenu      = document.getElementById("btn-back-menu");

const mixForm          = document.getElementById("mix-form");
const statusEl         = document.getElementById("status");
const questionsEl      = document.getElementById("questions");
const examMetaEl       = document.getElementById("exam-meta");
const toggleAnswersBtn = document.getElementById("toggle-answers-btn");
const exportPdfBtn     = document.getElementById("export-pdf-btn");
const generateBtn      = document.getElementById("generate-btn");
const daySelect        = document.getElementById("day");
const languageField    = document.getElementById("language-field");
const finishBtn        = document.getElementById("finish-btn");
const finishFooter     = document.getElementById("finish-footer");
const progressContainer = document.getElementById("progress-container");
const progressFill     = document.getElementById("progress-fill");
const progressText     = document.getElementById("progress-text");
const confirmModal     = document.getElementById("confirm-modal");
const modalTitle       = document.getElementById("modal-title");
const modalMessage     = document.getElementById("modal-message");
const modalCancelBtn   = document.getElementById("modal-cancel-btn");
const modalConfirmBtn  = document.getElementById("modal-confirm-btn");

const itaPanel         = document.getElementById("ita-generator-panel");
const btnMenuIta       = document.getElementById("btn-menu-ita");
const btnBackMenuIta   = document.getElementById("btn-back-menu-ita");
const itaMixForm       = document.getElementById("ita-mix-form");

let pendingConfirm = null;

// ─── Utilitários ──────────────────────────────────────────────────────────────
function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function updateFinishFooterVisibility() {
  finishFooter.classList.toggle("hidden", !state.currentExam || state.examFinished);
}

function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img alt="$1" src="$2" style="max-width: 100%; height: auto; display: block; margin: 10px 0;">');
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return html;
}

function showConfirmModal(title, message) {
  return new Promise((resolve) => {
    pendingConfirm = resolve;
    modalTitle.textContent = title;
    modalMessage.textContent = message;
    confirmModal.classList.remove("hidden");
    modalConfirmBtn.focus();
  });
}

function closeConfirmModal(result = false) {
  if (!pendingConfirm) return;

  const resolve = pendingConfirm;
  pendingConfirm = null;
  confirmModal.classList.add("hidden");

  resolve(result);
}

// ─── Identificação do aluno ────────────────────────────────────────────────
function getStudentId() {
  const key = "enem-student-id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(key, id);
  }
  return id;
}

// ─── Persistência de respostas ─────────────────────────────────────────────
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
  // Bloqueia alteração após finalizar
  if (!state.currentExam || state.examFinished) return;
  state.answers[String(questionIndex)] = letter;
  localStorage.setItem(
    getAnswersStorageKey(state.currentExam.id),
    JSON.stringify(state.answers)
  );
}

// ─── Barra de progresso horizontal ────────────────────────────────────────
function updateProgress() {
  if (!state.currentExam) return;
  const total    = state.currentExam.questions.length;
  const answered = Object.keys(state.answers).length;
  const pct      = total > 0 ? Math.round((answered / total) * 100) : 0;
  progressFill.style.width = `${pct}%`;
  progressText.textContent = `${answered}/${total} respondidas`;
}

// ─── Renderização do cabeçalho do simulado ENEM ────────────────────────────
function renderExamMeta(exam) {
  examMetaEl.classList.remove("hidden");
  const languageMeta = exam.day === 1 ? ` · Idioma: ${exam.language}` : "";
  examMetaEl.innerHTML = `
    <strong>Simulado gerado</strong> &mdash; ID: ${exam.id}<br>
    Dia ${exam.day} &nbsp;·&nbsp; Anos sorteados: ${exam.years.join(" → ")}<br>
    Caderno ${exam.caderno}${languageMeta} &nbsp;·&nbsp; ${exam.questions.length} questões
  `;
}

// ─── Renderização das questões ENEM ────────────────────────────────────────
function renderQuestions(exam) {
  questionsEl.innerHTML = exam.questions
    .map((question) => {
      const savedAnswer = state.answers[String(question.mixedIndex)];
      const alternatives = question.alternatives
        .map((alt) => {
          const checked    = savedAnswer === alt.letter ? "checked" : "";
          const isSelected = savedAnswer === alt.letter ? "selected" : "";
          const isCorrect  = (state.showAnswers && state.examFinished && alt.isCorrect) ? "correct" : "";
          const isWrong    = (state.showAnswers && state.examFinished && savedAnswer === alt.letter && !alt.isCorrect) ? "wrong" : "";
          const disabled   = state.examFinished ? "disabled" : "";
          const lockedClass = state.examFinished ? "locked" : "";

          return `
            <li class="${[isCorrect, isSelected, isWrong].filter(Boolean).join(" ")}">
              <label class="answer-option ${lockedClass}">
                <input
                  type="radio"
                  name="question-${question.mixedIndex}"
                  value="${alt.letter}"
                  data-question-index="${question.mixedIndex}"
                  ${checked}
                  ${disabled}
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
            <h3>Questão ${question.mixedIndex}</h3>
            <span class="question-origin">ENEM ${question.originalYear} · item ${question.originalIndex}</span>
          </div>
          <div class="context">${renderMarkdown(question.context)}</div>
          ${question.alternativesIntroduction
            ? `<div class="intro">${renderMarkdown(question.alternativesIntroduction)}</div>`
            : ""}
          <ul class="alternatives">${alternatives}</ul>
          <span class="answer-badge ${(state.showAnswers && state.examFinished) ? "" : "hidden"}">
            Gabarito: ${question.correctAlternative}
          </span>
        </article>
      `;
    })
    .join("");

  if (!state.examFinished) {
    questionsEl.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.addEventListener("change", (event) => {
        saveAnswer(event.target.dataset.questionIndex, event.target.value);
        updateProgress();
        renderQuestions(exam);
      });
    });
  }
}

// ─── Renderização das questões ITA ─────────────────────────────────────────
// ─── Renderização das questões ITA ─────────────────────────────────────────
function renderItaQuestions(exam) {
  questionsEl.innerHTML = exam.questions
    .map((question) => {
      const savedAnswer = state.answers[String(question.mixedIndex)];
      
      const letters = ['A', 'B', 'C', 'D', 'E'];
      let alternativesHtml = "";
      
      // Monta as opções (A, B, C, D, E) para a Fase 1
      if (exam.phase === 1) {
        alternativesHtml = `<ul class="alternatives" style="margin-top: 15px;">` + letters.map(letter => {
          const checked    = savedAnswer === letter ? "checked" : "";
          const isSelected = savedAnswer === letter ? "selected" : "";
          const isCorrect  = (state.showAnswers && state.examFinished && question.correctAlternative === letter) ? "correct" : "";
          const isWrong    = (state.showAnswers && state.examFinished && savedAnswer === letter && question.correctAlternative !== letter) ? "wrong" : "";
          const disabled   = state.examFinished ? "disabled" : "";
          const lockedClass = state.examFinished ? "locked" : "";
          // Após renderizar tudo, manda o MathJax processar as fórmulas LaTeX do ITA
  if (window.MathJax) {
    MathJax.typesetPromise([questionsEl]).catch((err) => console.log('Erro no MathJax: ', err));
  }

          return `
            <li class="${[isCorrect, isSelected, isWrong].filter(Boolean).join(" ")}">
              <label class="answer-option ${lockedClass}">
                <input type="radio" name="ita-q-${question.mixedIndex}" value="${letter}" data-question-index="${question.mixedIndex}" ${checked} ${disabled}>
                <span>Marcar Alternativa <strong>${letter}</strong></span>
              </label>
            </li>
          `;
        }).join("") + `</ul>`;
      }

      // Prevenção caso falte algum dado de matéria/ano no JSON
      const materiaName = question.materia ? question.materia.toUpperCase() : "GERAL";
      const anoName = question.ano || "";
     
       return `
        <article class="question-card" data-index="${question.mixedIndex}">
          <div class="question-header">
            <h3>Questão ${question.mixedIndex}</h3>
            <span class="question-origin">ITA ${anoName} · ${materiaName}</span>
          </div>
          
          <div class="context" style="margin-bottom: 20px; font-size: 1.05rem;">
            ${renderMarkdown(question.context)}
          </div>
          
          <details style="margin-bottom: 15px; cursor: pointer; color: var(--muted); font-size: 0.85rem;">
            <summary>Ver imagem original da prova</summary>
            <div style="text-align: center; margin-top: 10px;">
              <img src="/ita-assets/${question.imagem}" alt="Questão original" style="max-width: 100%; border-radius: 8px;">
            </div>
          </details>

          ${alternativesHtml}
          
          <span class="answer-badge ${(state.showAnswers && state.examFinished) ? "" : "hidden"}">
            Gabarito: ${question.correctAlternative || "Consulte o gabarito oficial"}
          </span>
        </article>
      `;

    })
    .join("");

  if (!state.examFinished) {
    questionsEl.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.addEventListener("change", (event) => {
        saveAnswer(event.target.dataset.questionIndex, event.target.value);
        updateProgress();
        renderItaQuestions(exam); // Re-renderiza para aplicar estado visual "selected"
      });
    });
  }
}

// ─── Geração do simulado ENEM ──────────────────────────────────────────────
async function generateMix(event) {
  event.preventDefault();

  const language = document.getElementById("language").value;
  const day      = Number(daySelect.value);

  if (state.currentExam && !state.examFinished) {
    setStatus("Finalize o simulado atual antes de gerar um novo.");
    return;
  }
  questionsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  
  state.examFinished = false;
  state.showAnswers  = false;
  state.result       = null;

  updateFinishFooterVisibility();
  finishBtn.disabled   = true;
  toggleAnswersBtn.disabled    = true;
  toggleAnswersBtn.textContent = "Mostrar Gabarito";
  setStatus("Gerando simulado único…");

  try {
    const response = await fetch("/api/mix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ day, language, studentId: getStudentId() }),
    });

    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Erro ao gerar simulado.");

    state.currentExam = payload;
    updateFinishFooterVisibility();

    loadSavedAnswers(payload.id);
    renderExamMeta(payload);
    
    progressContainer.classList.remove("hidden");
    updateProgress();

    renderQuestions(payload);

    finishBtn.disabled = false;
    exportPdfBtn.href = `/api/mix/${payload.id}/pdf`;
    exportPdfBtn.classList.remove("disabled", "hidden");

    setStatus(`Simulado pronto com ${payload.questions.length} questões.`);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    generateBtn.disabled = false;
  }
}

// ─── Geração do simulado ITA ───────────────────────────────────────────────
async function generateItaMix(event) {
  event.preventDefault();

  const subject = document.getElementById("ita-subject").value;
  const phase   = Number(document.getElementById("ita-phase").value);
  const itaStatusEl = document.getElementById("ita-status");

  if (state.currentExam && !state.examFinished) {
    itaStatusEl.textContent = "Finalize o simulado atual antes de gerar um novo.";
    itaStatusEl.classList.add("error");
    return;
  }

  itaStatusEl.textContent = "Gerando simulado ITA...";
  itaStatusEl.classList.remove("error");

  try {
    const response = await fetch("/api/ita/mix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, phase, studentId: getStudentId() }),
    });

    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Erro ao gerar simulado ITA.");

    // Esconde o painel
    document.getElementById("ita-generator-panel").classList.add("hidden");
    questionsEl.scrollIntoView({ behavior: "smooth", block: "start" });
    
    state.currentExam = payload;
    state.examFinished = false;
    state.showAnswers  = false;
    state.result       = null;

    updateFinishFooterVisibility();
    finishBtn.disabled = false;
    toggleAnswersBtn.disabled    = true;
    toggleAnswersBtn.textContent = "Mostrar Gabarito";
    exportPdfBtn.classList.add("hidden"); // Sem PDF pro ITA por enquanto

    // Preenche o cabeçalho
    examMetaEl.classList.remove("hidden");
    examMetaEl.innerHTML = `
      <strong>Simulado ITA</strong> &mdash; ID: ${payload.id}<br>
      Fase ${payload.phase} &nbsp;·&nbsp; Disciplina: ${payload.subject.toUpperCase()}<br>
      ${payload.questions.length} questões
    `;

    loadSavedAnswers(payload.id);
    progressContainer.classList.remove("hidden");
    updateProgress();

    renderItaQuestions(payload);
    itaStatusEl.textContent = "";

  } catch (error) {
    itaStatusEl.textContent = error.message;
    itaStatusEl.classList.add("error");
  }
}

// ─── Mostrar / ocultar gabarito ───────────────────────────────────────────
function toggleAnswers() {
  if (!state.currentExam || !state.examFinished) return;

  state.showAnswers = !state.showAnswers;
  toggleAnswersBtn.textContent = state.showAnswers ? "Ocultar Gabarito" : "Mostrar Gabarito";
  
  if (state.currentExam.phase) {
    renderItaQuestions(state.currentExam);
  } else {
    renderQuestions(state.currentExam);
  }
}

// ─── Cálculo de resultado ──────────────────────────────────────────────────
function calcResult() {
  let correct = 0;
  let wrong = 0;
  let blank = 0;

  const areas = {};
  const total = state.currentExam.questions.length;

  state.currentExam.questions.forEach((question) => {
    const answer = state.answers[String(question.mixedIndex)];
    // Usa a propriedade subject do ITA ou area do ENEM
    const area = question.area || question.subject || "Geral";

    if (!areas[area]) {
      areas[area] = { total: 0, correct: 0, wrong: 0, blank: 0 };
    }

    areas[area].total++;

    if (!answer) {
      blank++;
      areas[area].blank++;
    } else if (answer === question.correctAlternative) {
      correct++;
      areas[area].correct++;
    } else {
      wrong++;
      areas[area].wrong++;
    }
  });

  return {
    total,
    correct,
    wrong,
    blank,
    percentage: Math.round((correct / total) * 100),
    areas,
  };
}

// ─── Renderização da tela de resultado ────────────────────────────────────
function renderResult() {
  const r = state.result;
  if (!r) return;

  let motivMsg, motivClass;
  if (r.percentage >= 80) {
    motivMsg   = "🏆 Excelente desempenho! Você está muito bem preparado.";
    motivClass = "motiv-excellent";
  } else if (r.percentage >= 60) {
    motivMsg   = "👍 Bom desempenho! Revise os tópicos com maior dificuldade.";
    motivClass = "motiv-good";
  } else {
    motivMsg   = "📚 Continue estudando! Com dedicação você chega lá.";
    motivClass = "motiv-needs-work";
  }

  let worstArea = null;
  let worstPct  = Infinity;
  
  Object.entries(r.areas).forEach(([area, data]) => {
    const answered = data.correct + data.wrong;
    if (answered === 0) return;
    const pct = (data.correct / answered) * 100;
    if (pct < worstPct) {
      worstPct = pct;
      worstArea = area;
    }
  });

  const areasHTML = Object.entries(r.areas)
    .sort(([, a], [, b]) => {
      const pa = a.total > 0 ? a.correct / a.total : 0;
      const pb = b.total > 0 ? b.correct / b.total : 0;
      return pb - pa;
    })
    .map(([area, data]) => {
      const pct      = data.total > 0 ? Math.round((data.correct / data.total) * 100) : 0;
      const isWorst  = area === worstArea;
      
      return `
        <div class="result-summary" style="margin-bottom: 15px; padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px;">
            <div style="font-weight: bold; margin-bottom: 5px; text-transform: capitalize;">${area} ${isWorst ? "⚠️" : ""}</div>
            <div style="display: flex; gap: 15px; font-size: 0.9em;">
              <span><strong>${data.correct}</strong> Acertos</span>
              <span><strong>${data.wrong}</strong> Erros</span>
              <span><strong>${pct}%</strong> Aproveitamento</span>
            </div>
        </div>
      `;
    })
    .join("");

  const radius = 52;
  const circ   = +(2 * Math.PI * radius).toFixed(2);
  const filled = +((circ * r.percentage) / 100).toFixed(2);
  const ringColor = r.percentage >= 80 ? "#16a34a" : r.percentage >= 60 ? "#f59e0b" : "#dc2626";

  const ringHTML = `
    <div class="progress-ring-wrap">
      <svg class="progress-ring" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
        <circle cx="60" cy="60" r="${radius}" fill="none" stroke="#e5e7eb" stroke-width="10"/>
        <circle cx="60" cy="60" r="${radius}" fill="none"
          stroke="${ringColor}" stroke-width="10"
          stroke-dasharray="${filled} ${circ}"
          stroke-dashoffset="${circ / 4}"
          stroke-linecap="round"
        />
        <text x="60" y="56" text-anchor="middle" font-size="20" font-weight="700" fill="${ringColor}">${r.percentage}%</text>
        <text x="60" y="74" text-anchor="middle" font-size="11" fill="#6b7280">acertos</text>
      </svg>
    </div>
  `;

  // Checa se é ENEM ou ITA para formatar o subtítulo
  const subtitleInfo = state.currentExam.day 
    ? `Dia ${state.currentExam.day}` 
    : `Fase ${state.currentExam.phase}`;

  questionsEl.innerHTML = `
    <div class="result-card" id="result-card">
      <div class="result-header">
        <h2 class="result-title">🎉 Simulado Finalizado!</h2>
        <p class="result-subtitle">
          ${state.currentExam.questions.length} questões &nbsp;·&nbsp; ${subtitleInfo}
        </p>
      </div>

      <div class="result-body">
        ${ringHTML}
        <div class="result-counters">
          <div class="counter counter-correct">
            <span class="counter-num">${r.correct}</span>
            <span class="counter-label">Acertos</span>
          </div>
          <div class="counter counter-wrong">
            <span class="counter-num">${r.wrong}</span>
            <span class="counter-label">Erros</span>
          </div>
          <div class="counter counter-blank">
            <span class="counter-num">${r.blank}</span>
            <span class="counter-label">Em branco</span>
          </div>
        </div>
      </div>

      <div class="motiv-msg ${motivClass}">${motivMsg}</div>

      <div class="areas-section">
        <h3 class="areas-title">📊 Desempenho</h3>
        ${areasHTML}
      </div>

      <div class="result-actions">
        <button class="btn btn-primary" id="show-gabarito-btn">📋 Ver Gabarito</button>
      </div>
    </div>
  `;

  document.getElementById("show-gabarito-btn").addEventListener("click", () => {
    state.showAnswers = true;
    toggleAnswersBtn.textContent = "Ocultar Gabarito";
    if (state.currentExam.phase) {
      renderItaQuestions(state.currentExam);
    } else {
      renderQuestions(state.currentExam);
    }
    questionsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

// ─── Finalizar simulado ────────────────────────────────────────────────────
async function finishExam() {
  if (!state.currentExam || state.examFinished) return;

  const answered = Object.keys(state.answers).length;
  const total    = state.currentExam.questions.length;

  if (answered < total) {
    const ok = await showConfirmModal(
      "Questões em branco",
      `Você respondeu ${answered} de ${total} questões.\nDeseja finalizar mesmo assim?`
    );
    if (!ok) return;
  }

  const ok2 = await showConfirmModal(
    "Finalizar simulado",
    "Deseja realmente finalizar o simulado?\nDepois disso não será possível alterar as respostas."
  );
  if (!ok2) return;

  state.result       = calcResult();
  state.examFinished = true;

  finishBtn.disabled            = true;
  toggleAnswersBtn.disabled     = false;
  toggleAnswersBtn.textContent  = "Mostrar Gabarito";
  updateFinishFooterVisibility();
  progressContainer.classList.add("hidden");

  renderResult();
}

function updateLanguageVisibility() {
  languageField.classList.toggle("hidden", Number(daySelect.value) !== 1);
}

// ─── Event Listeners e Navegação ──────────────────────────────────────────

// Menu Principal -> ITA
btnMenuIta.addEventListener("click", () => {
  mainMenu.classList.add("hidden");
  itaPanel.classList.remove("hidden");
});

btnBackMenuIta.addEventListener("click", () => {
  itaPanel.classList.add("hidden");
  mainMenu.classList.remove("hidden");
});

// Menu Principal -> ENEM
btnMenuEnem.addEventListener("click", () => {
  mainMenu.classList.add("hidden");
  enemPanel.classList.remove("hidden");
});

btnBackMenu.addEventListener("click", () => {
  enemPanel.classList.add("hidden");
  mainMenu.classList.remove("hidden");
});

// Formulários
itaMixForm.addEventListener("submit", generateItaMix);
mixForm.addEventListener("submit", generateMix);

// Ações do Simulado
toggleAnswersBtn.addEventListener("click", toggleAnswers);
finishBtn.addEventListener("click", finishExam);

// Modal
modalCancelBtn.addEventListener("click", () => closeConfirmModal(false));
modalConfirmBtn.addEventListener("click", () => closeConfirmModal(true));
confirmModal.addEventListener("click", (event) => {
  if (event.target === confirmModal) closeConfirmModal(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !confirmModal.classList.contains("hidden")) {
    closeConfirmModal(false);
  }
});
daySelect.addEventListener("change", updateLanguageVisibility);
updateLanguageVisibility();
updateFinishFooterVisibility();