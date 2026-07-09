"use strict";

// Клиент веб-интерфейса Бункера: поллинг состояния, журнал, ход человека,
// панели ботов с новыми заметками за раунд и текущим контекстом модели.

const POLL_MS = 600;

let currentState = null;
let pollTimer = null;
let submitting = false;
const openContexts = new Set(); // id ботов, у кого раскрыт блок контекста

// ── Мини-помощник для DOM ──────────────────────────────────────
function h(tag, attrs, children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      if (value == null || value === false) continue;
      if (key === "class") el.className = value;
      else if (key === "text") el.textContent = value;
      else if (key.startsWith("on") && typeof value === "function") {
        el.addEventListener(key.slice(2), value);
      } else if (value === true) el.setAttribute(key, "");
      else el.setAttribute(key, value);
    }
  }
  const list = children == null ? [] : Array.isArray(children) ? children : [children];
  for (const child of list) {
    if (child == null) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

const $ = (id) => document.getElementById(id);

// ── Сеть ───────────────────────────────────────────────────────
async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function schedulePoll(delay = POLL_MS) {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(refresh, delay);
}

async function refresh() {
  try {
    const state = await api("/api/state");
    render(state);
    if (state.status === "advancing" || state.status === "idle") schedulePoll();
  } catch (error) {
    showError(`Нет связи с сервером: ${error.message}`);
    schedulePoll(1500);
  }
}

async function submit(body) {
  if (submitting) return;
  submitting = true;
  try {
    await api("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    hideError();
    await refresh();
  } catch (error) {
    showError(error.message);
  } finally {
    submitting = false;
  }
}

async function restart() {
  try {
    await api("/api/restart", { method: "POST" });
    hideError();
    await refresh();
  } catch (error) {
    showError(error.message);
  }
}

// ── Рендер ─────────────────────────────────────────────────────
function render(state) {
  currentState = state;
  renderMeta(state);
  renderLog(state);
  renderTurn(state);
  renderPlayers(state);

  const busy = state.status === "advancing" || state.status === "idle";
  $("thinking-chip").hidden = !busy;
  if (state.status === "error") showError(state.error || "Ошибка партии.");
}

function renderMeta(state) {
  const row = $("meta-row");
  row.replaceChildren(
    h("span", { class: "catastrophe" }, [
      h("span", { class: "tag tag-strong" }, "Катастрофа"),
      h("span", { class: "cat-text" }, state.catastrophe || "—"),
    ]),
    h("span", { class: "tag" }, `Раунд ${state.round_no}`),
    h("span", { class: "tag" }, `Мест ${state.capacity}`),
    h("span", { class: "tag tag-fern" }, `Выжившие ${state.alive_count}`),
  );
}

function renderLog(state) {
  const log = $("event-log");
  const items = (state.event_log || []).map((event) =>
    h("li", { class: `timeline-item phase-${event.phase}` }, [
      h("span", { class: "timeline-round" }, `Р${event.round_no}`),
      h("span", { class: "timeline-text" }, event.text),
    ]),
  );
  if (items.length === 0) {
    items.push(h("li", { class: "timeline-item" }, [h("span", { class: "timeline-text" }, "Партия начинается…")]));
  }
  log.replaceChildren(...items);
  const panel = log.closest(".panel-log");
  if (panel) panel.scrollTop = panel.scrollHeight;
}

function renderTurn(state) {
  const panel = $("turn-panel");

  if (state.status === "finished") {
    panel.replaceChildren(
      h("div", { class: "panel-title" }, "Партия окончена"),
      h("p", { class: "finale-msg" }, state.winner_message || "—"),
      h("div", { class: "btn-row" }, [
        h("button", { class: "btn btn-moss", onclick: restart }, "Новая партия"),
      ]),
    );
    return;
  }

  if (state.status !== "awaiting_human" || !state.pending) {
    panel.replaceChildren(
      h("div", { class: "waiting" }, [h("span", { class: "chip-dot" }), "Ход обрабатывается…"]),
    );
    return;
  }

  const pending = state.pending;
  const builders = {
    reveal: buildReveal,
    vote: buildVote,
    discuss: () => buildSpeech("Обсуждение", "Защитите своё место в бункере в двух-трёх предложениях."),
    last_word: () => buildSpeech("Последнее слово", "Вас исключают. Скажите пару прощальных фраз."),
  };
  const build = builders[pending.type];
  panel.replaceChildren(build ? build(pending) : h("div", { class: "waiting" }, "Неизвестный ход."));
}

function buildReveal(pending) {
  const options = (pending.hidden || []).map(([label, key], index) =>
    h("label", { class: "option" }, [
      h("input", { type: "radio", name: "reveal-card", value: key, checked: index === 0 }),
      h("span", { class: "opt-label" }, label),
      h("span", { class: "opt-value" }, pending.hand ? pending.hand[label] : ""),
    ]),
  );
  const onclick = () => {
    const checked = document.querySelector('input[name="reveal-card"]:checked');
    if (!checked) return showError("Выберите карту для раскрытия.");
    submit({ card: checked.value });
  };
  return h("div", { class: "turn-body" }, [
    h("div", { class: "panel-title" }, `Раскрытие карты · раунд ${pending.round}`),
    h("p", { class: "panel-hint" }, "Выберите характеристику, которую откроете всем."),
    h("div", { class: "options" }, options),
    h("div", { class: "btn-row" }, [h("button", { class: "btn btn-moss", onclick }, "Раскрыть")]),
  ]);
}

function buildVote(pending) {
  const options = (pending.candidates || []).map((candidate, index) =>
    h("label", { class: "option" }, [
      h("input", { type: "radio", name: "vote-target", value: candidate.id, checked: index === 0 }),
      h("span", { class: "opt-value" }, candidate.name),
    ]),
  );
  const onclick = () => {
    const checked = document.querySelector('input[name="vote-target"]:checked');
    if (!checked) return showError("Выберите, за чьё исключение голосовать.");
    submit({ target_id: Number(checked.value) });
  };
  return h("div", { class: "turn-body" }, [
    h("div", { class: "panel-title" }, "Голосование за исключение"),
    h("p", { class: "panel-hint" }, "Голос анонимный: другие не увидят, за кого вы голосовали."),
    h("div", { class: "options" }, options),
    h("div", { class: "btn-row" }, [h("button", { class: "btn btn-moss", onclick }, "Голосовать")]),
  ]);
}

function buildSpeech(title, hint) {
  const area = h("textarea", { placeholder: "ваша реплика…" });
  const onclick = () => {
    const text = area.value.trim();
    if (!text) return showError("Текст не может быть пустым.");
    submit({ text });
  };
  return h("div", { class: "turn-body" }, [
    h("div", { class: "panel-title" }, title),
    h("p", { class: "panel-hint" }, hint),
    area,
    h("div", { class: "btn-row" }, [h("button", { class: "btn btn-moss", onclick }, "Отправить")]),
  ]);
}

function renderPlayers(state) {
  const grid = $("players-grid");
  grid.replaceChildren(...(state.players || []).map(renderPlayerCard));
}

function renderPlayerCard(player) {
  const classes = ["bot-card"];
  if (player.is_human) classes.push("is-human");
  if (!player.is_alive) classes.push("is-dead");

  const status = player.is_human
    ? h("span", { class: "status-pill" }, "Вы")
    : h("span", { class: `status-pill ${player.is_alive ? "alive" : "dead"}` },
        player.is_alive ? "жив" : "исключён");

  const revealed = new Set(player.revealed || []);
  const cardTags = Object.entries(player.cards || {}).map(([label, value]) =>
    revealed.has(label)
      ? h("span", { class: "card-tag" }, `${label}: ${value}`)
      : h("span", { class: "card-tag hidden-tag", title: value }, label),
  );

  const parts = [
    h("div", { class: "bot-head" }, [h("span", { class: "bot-name" }, player.name), status]),
    h("div", { class: "card-tags" }, cardTags),
  ];

  if (!player.is_human) {
    parts.push(renderFreshNotes(player));
    parts.push(renderContext(player));
  }
  return h("div", { class: classes.join(" ") }, parts);
}

function renderFreshNotes(player) {
  const fresh = (player.round_notes || "").trim();
  return h("div", {}, [
    h("div", { class: "block-label" }, "Новые заметки этого раунда"),
    h("div", { class: `notes-fresh ${fresh ? "" : "empty"}` }, fresh || "пока пусто"),
  ]);
}

function renderContext(player) {
  const exact = player.context_tokens_exact;
  const gauge = h("span", { class: "gauge" }, [
    exact ? "" : h("span", { class: "approx" }, "≈"),
    `${player.context_tokens} токенов · ${player.context_chars} симв.`,
  ]);

  const history = (player.notes_by_round || []).map((entry) =>
    h("li", {}, [h("span", { class: "nr" }, `Р${entry.round}`), entry.text]),
  );

  const details = h("details", { class: "context" }, [
    h("summary", {}, [h("span", { class: "context-title" }, "Контекст модели"), gauge]),
    h("pre", { class: "context-pre" }, player.context || ""),
    history.length ? h("div", { class: "block-label" }, "Все заметки по раундам") : null,
    history.length ? h("ul", { class: "notes-log" }, history) : null,
  ]);
  if (openContexts.has(player.id)) details.open = true;
  details.addEventListener("toggle", () => {
    if (details.open) openContexts.add(player.id);
    else openContexts.delete(player.id);
  });
  return details;
}

// ── Ошибки ─────────────────────────────────────────────────────
function showError(message) {
  const chip = $("error-chip");
  chip.textContent = message;
  chip.hidden = false;
}

function hideError() {
  $("error-chip").hidden = true;
}

refresh();
