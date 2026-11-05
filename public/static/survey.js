"use strict";
// Single-page survey. Wording comes from survey/survey_copy.md; option values must
// match the codes in app/schema.py. Nothing is sent until /api/submit, apart from
// /api/start, which only fetches this participant's screen plan.

const CFG = window.SURVEY_CONFIG || {};
const PILOT = new URLSearchParams(location.search).get("pilot") === "1";
const main = document.getElementById("main");
const bar = document.getElementById("progress");

const state = {
  s1: null, path: null, anchorNA: false, S: null, p2: null,   // S = anchor CTC in LPA
  token: null, plan: [], choices: [], a: {},                    // a = answers sent at submit
  times: {}, t0: 0,
};

const LEVELS = {
  varpay: {
    cash: "All monthly salary",
    bonus: "80% salary + 20% year-end bonus",
    equity: "80% salary + 20% ESOPs (4-year vest)",
  },
  arrangement: {
    onsite: "On-site, 5 days a week",
    hybrid: "Hybrid, 2–3 office days a week",
    remote: "Fully remote",
  },
  autonomy: {
    assigned: "Tasks assigned and closely tracked",
    some: "Tasks assigned; some say in how",
    choose: "You choose what and how",
  },
  growth: {
    none: "No learning support or promotion track",
    mentorship: "Mentor + learning budget",
    track: "Promotion track + learning budget",
  },
};
const OFFER_ROWS = [
  ["Total CTC", (p) => rupees(p.salary_level * state.S)],
  ["How it's paid", (p) => LEVELS.varpay[p.varpay]],
  ["Where you work", (p) => LEVELS.arrangement[p.arrangement]],
  ["Weekly hours", (p) => `${p.hours} hours`],
  ["Say over your work", (p) => LEVELS.autonomy[p.autonomy]],
  ["Growth", (p) => LEVELS.growth[p.growth]],
];

// ---------- helpers ----------

const $ = (sel) => main.querySelector(sel);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const round1 = (x) => Math.round(x * 10) / 10;           // CTC display rule: nearest 0.1 LPA
const lpa = (x) => { const r = round1(x); return Number.isInteger(r) ? String(r) : r.toFixed(1); };
const rupees = (x) => `₹${lpa(x)} LPA`;
const checked = (name) => main.querySelector(`input[name="${name}"]:checked`)?.value ?? null;
const pick = () => (Math.random() < 0.5 ? "positional_first" : "absolute_first");

// A config value, or a highlighted [LABEL] so unfilled placeholders are obvious in the pilot.
const ph = (key, label) => (CFG[key] ? esc(CFG[key]) : `<span class="todo">[${label}]</span>`);

function radios(name, options, { inline = false, scale = false } = {}) {
  return `<div class="radios${inline ? " inline" : ""}${scale ? " scale" : ""}">` + options.map(([value, label]) =>
    `<label class="radio"><input type="radio" name="${name}" value="${esc(value)}"><span>${label}</span></label>`,
  ).join("") + "</div>";
}

function guard(e) { e.preventDefault(); e.returnValue = ""; }

// Time on each screen, in ms. Descriptive only; never an exclusion rule.
let current = null, enteredAt = 0;
function enter(id) {
  if (current) state.times[current] = (state.times[current] || 0) + Math.round(performance.now() - enteredAt);
  current = id;
  enteredAt = performance.now();
}

function flow() {
  const pages = ["consent", "s1", "anchor", "instructions"];
  for (let i = 1; i <= 10; i++) pages.push(`choice${i}`);
  pages.push("b1", "b2", "b3", "b4", "background", state.path === "student" ? "student" : "work", "feedback");
  return pages;
}

// Render a page. `valid` is re-checked on every input; Next stays disabled until it passes.
function show(id, html, { valid = () => true, next = null, nextLabel = "Next" } = {}) {
  enter(id);
  const pages = flow(), i = pages.indexOf(id);
  bar.style.width = i < 0 ? "100%" : `${(100 * i) / pages.length}%`;
  main.innerHTML = html + (next
    ? `<div class="actions"><button type="button" id="next" class="primary">${nextLabel}</button><p id="err" class="err" role="alert"></p></div>`
    : "");
  window.scrollTo(0, 0);
  const heading = main.querySelector("h1, h2");      // move screen-reader focus to the new page
  if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
  main.oninput = main.onchange = null;
  if (!next) return;
  const btn = $("#next");
  const refresh = () => { btn.disabled = !valid(); };
  main.oninput = main.onchange = refresh;
  refresh();
  btn.onclick = () => { if (valid()) next(); };
}

const fail = (msg) => { const e = $("#err"); if (e) e.textContent = msg; };

async function post(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

// ---------- 0. consent ----------

function consent() {
  show("consent", `
    <h1>Job choices study</h1>
    <p>We're Prajna Penmetsa and Aayush Khatanhar, students at IIIT Hyderabad. This survey, on how people in tech choose between job offers, is part of our course project for ${ph("course", "COURSE")}, supervised by ${ph("instructor", "INSTRUCTOR")}.</p>
    <ul class="facts">
      <li><b>About 7 minutes.</b> Pick between 10 pairs of made-up job offers, then answer a few short questions, including your pay.</li>
      <li><b>Who can take part:</b> anyone 18 or older who is a student or works in a tech role.</li>
      <li><b>Voluntary.</b> Close the page at any time; unfinished answers are thrown away.</li>
      <li><b>Anonymous.</b> We don't ask your name, email or employer, or store your IP address with your answers. Results are only reported as group averages.</li>
    </ul>
    <p class="muted">${ph("ethicsLine", "ETHICS LINE")}</p>
    <label class="check"><input type="checkbox" id="agree"><span>I'm 18 or older, I've read the above, and I agree to take part.</span></label>`,
  {
    nextLabel: "Start",
    valid: () => $("#agree").checked,
    next: () => {
      state.t0 = performance.now();
      window.addEventListener("beforeunload", guard);
      screener();
    },
  });
}

// ---------- 1. screener ----------

function screener() {
  show("s1", `<h2>Which best describes you right now?</h2>` + radios("s1", [
    ["student_ug", "I'm a student (undergraduate)"],
    ["student_pg", "I'm a student (Master's or PhD)"],
    ["pro", "I work full-time in a tech role (software, data, IT, hardware, product, design, etc.)"],
    ["between", "I'm between jobs, and my last job was in a tech role"],
    ["nontech", "I work full-time in a non-tech role"],
    ["none", "None of these"],
  ]), {
    valid: () => !!checked("s1"),
    next: () => {
      const v = checked("s1");
      if (v === "nontech" || v === "none") return screenOut();
      state.s1 = v;
      state.path = v.startsWith("student") ? "student" : v === "pro" ? "professional" : "between";
      anchor();
    },
  });
}

function screenOut() {
  window.removeEventListener("beforeunload", guard);
  show("screenout", `<h2>Thanks for your interest</h2>
    <p>This study is for students and people working in tech, so that's the end of the survey for you. Nothing you entered has been saved.</p>`);
}

// ---------- 2. pay anchor ----------

function ctcProblem(text) {
  const x = Number(text.trim().replace(/,/g, ""));
  if (!text.trim() || !Number.isFinite(x)) return "Please enter a number, for example 12.";
  if (x > 1000) return "That looks like rupees rather than lakhs. For example, enter 12 for ₹12,00,000 a year.";
  if (x < 1) return "Please enter your CTC in lakhs per year. For example, enter 4.5 for ₹4,50,000.";
  return "";
}

function anchor() {
  const student = state.path === "student";
  const question = {
    professional: "What's your current total CTC per year, in LPA? Include bonus and stock; a best guess is fine.",
    between: "What was the total CTC per year of your last job, in LPA? Include bonus and stock; a best guess is fine.",
    student: "What total CTC per year do you have, or expect, for your first full-time job, in LPA?",
  }[state.path];
  show("anchor", `
    <p class="muted">We only use this to set realistic pay in the offers.</p>
    <h2><label for="ctc">${question}</label></h2>
    <div class="num"><input id="ctc" type="text" inputmode="decimal" autocomplete="off" placeholder="e.g. 12"><span>LPA</span></div>
    <p id="ctc-msg" class="err" role="alert"></p>
    <label class="check"><input type="checkbox" id="na"><span>Prefer not to say</span></label>
    ${student ? `<div id="p2"><h3>Is that an actual offer, or your estimate?</h3>${radios("p2", [["offer", "I have this offer"], ["estimate", "It's my estimate"]])}</div>` : ""}`,
  {
    valid: () => {
      const na = $("#na").checked, input = $("#ctc");
      input.disabled = na;
      if (student) $("#p2").hidden = na;
      const msg = na ? "" : ctcProblem(input.value);
      $("#ctc-msg").textContent = input.value.trim() ? msg : "";
      return na || (!msg && (!student || !!checked("p2")));
    },
    next: async () => {
      state.anchorNA = $("#na").checked;
      state.S = state.anchorNA ? 12 : round1(Number($("#ctc").value.trim().replace(/,/g, "")));
      state.p2 = state.anchorNA ? null : checked("p2");
      const btn = $("#next");
      btn.disabled = true;
      btn.textContent = "Loading…";
      try {
        const data = await post("api/start", { pilot: PILOT });
        state.token = data.token;
        state.plan = data.screens;
        instructions();
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "Try again";
        fail("We couldn't reach the survey server. Check your connection and try again.");
      }
    },
  });
}

// ---------- 3. instructions ----------

function instructions() {
  const basis = state.anchorNA ? "set around a typical CTC" : "set around the pay you told us";
  show("instructions", `
    <h2>How this part works</h2>
    <p>You'll see <b>10 pairs of job offers</b>. Pick the one you'd accept. Both are full-time jobs in your field and city, identical except for the six features shown.</p>
    <ul class="facts">
      <li><b>Total CTC</b> is yearly pay before tax, ${basis}. It's the same whatever the hours.</li>
      <li><b>Year-end bonus</b> is guaranteed, not linked to performance.</li>
      <li><b>ESOPs</b> are stock options in a private company. They can only be cashed if it's sold or goes public, which may never happen.</li>
    </ul>
    <p>There are no right or wrong answers, and you can't go back.</p>`,
  { nextLabel: "Start", next: () => choice(1) });
}

// ---------- 4. choice screens ----------

function choice(n) {
  const screen = state.plan[n - 1];
  const rows = OFFER_ROWS.map(([label, text]) =>
    `<div class="row"><div class="label">${label}</div><div class="cell">${text(screen.A)}</div><div class="cell">${text(screen.B)}</div></div>`).join("");
  show(`choice${n}`, `
    <p class="step">Offer ${n} of 10</p>
    <h2>Which job would you accept?</h2>
    <div class="offer">
      <div class="row head"><div class="label"></div><div class="cell">Job A</div><div class="cell">Job B</div></div>
      ${rows}
      <div class="row pick"><div class="label"></div>
        <div class="cell"><button type="button" class="primary" data-side="A" disabled>Accept Job A</button></div>
        <div class="cell"><button type="button" class="primary" data-side="B" disabled>Accept Job B</button></div>
      </div>
    </div>`);
  const shownAt = performance.now();
  const buttons = main.querySelectorAll("[data-side]");
  setTimeout(() => buttons.forEach((b) => { b.disabled = false; }), 400);   // a double tap can't skip a screen
  buttons.forEach((b) => {
    b.onclick = () => {
      buttons.forEach((x) => { x.disabled = true; });
      state.choices.push({
        set_id: screen.set_id, chose: b.dataset.side, rt_ms: Math.round(performance.now() - shownAt),
        ctc_A: round1(screen.A.salary_level * state.S), ctc_B: round1(screen.B.salary_level * state.S),
      });
      if (n < 10) choice(n + 1); else b1();
    };
  });
}

// ---------- 5. add-on blocks ----------

function priceList(id, intro, [headA, headB], rows, question, noneLabel, onNext) {
  show(id, `${intro}
    <table class="mpl"><thead><tr><th>Row</th><th>${headA}</th><th>${headB}</th></tr></thead><tbody>
      ${rows.map(([a, b], i) => `<tr><td>${i + 1}</td><td>${a}</td><td>${b}</td></tr>`).join("")}
    </tbody></table>
    <h3>${question}</h3>
    ${radios(id, [...rows.map((_, i) => [String(i + 1), `Row ${i + 1}`]), ["none", noneLabel]], { inline: true })}`,
  { valid: () => !!checked(id), next: () => onNext(checked(id)) });
  // The "None" option reads better on its own line.
  main.querySelector(`input[name="${id}"][value="none"]`).closest(".radio").style.gridColumn = "1 / -1";
}

function b1() {
  priceList("b1", `
    <h2>Money now or later</h2>
    <p>Your employer owes you a one-time payment: <b>₹2,00,000 today</b>, or more <b>in 12 months</b>. Both are guaranteed.</p>`,
  ["Today", "In 12 months"],
  ["₹2,10,000", "₹2,20,000", "₹2,40,000", "₹2,70,000", "₹3,00,000"].map((x) => ["₹2,00,000", x]),
  "From which row would you wait?",
  "None — I'd take ₹2,00,000 today in every row",
  (v) => { state.a.b1_switch = v; b2(); });
}

function b2() {
  priceList("b2", `
    <h2>A sure amount or shares</h2>
    <p>A one-time grant from your employer: <b>₹2,00,000 for sure</b>, or <b>shares</b> that turn out to be worth ₹4,00,000 or nothing. You find out straight away.</p>`,
  ["For sure", "Chance the shares pay ₹4,00,000"],
  [["30%", "3 in 10"], ["50%", "5 in 10"], ["65%", "about 2 in 3"], ["80%", "8 in 10"], ["95%", "19 in 20"]]
    .map(([p, f]) => ["₹2,00,000", `${p} (${f})`]),
  "From which row would you take the shares?",
  "None — I'd take ₹2,00,000 for sure in every row",
  (v) => { state.a.b2_switch = v; b3(); });
}

// B3: which world is listed first is randomised and recorded.
function twoWorlds(id, intro, worlds, onNext) {
  const order = pick();
  const keys = order === "positional_first" ? ["positional", "absolute"] : ["absolute", "positional"];
  show(id, `<h2>Two worlds</h2><p>${intro}</p>` + radios(id, keys.map((k) => [k, worlds[k]])),
    { valid: () => !!checked(id), next: () => onNext(checked(id), order) });
}

// The answer keeps its b3a_* names so the export columns stay as pre-registered.
function b3() {
  const S = state.S;
  twoWorlds("b3",
    "Prices are the same in both worlds. Which would you rather live in?",
    {
      positional: `You earn ${rupees(S)} a year. Other people in your field earn ${rupees(S / 2)} on average.`,
      absolute: `You earn ${rupees(2 * S)} a year. Other people in your field earn ${rupees(4 * S)} on average.`,
    },
    (choice, order) => { Object.assign(state.a, { b3a_choice: choice, b3a_order: order }); b4(); });
}

function b4() {
  const S = state.S;
  const rows = [
    ["b4_ctc", "Total CTC", `${rupees(0.8 * S)} to ${rupees(1.25 * S)}`],
    ["b4_varpay", "How it's paid", "All salary, or 20% as bonus or ESOPs"],
    ["b4_arrangement", "Where you work", "On-site, hybrid or remote"],
    ["b4_hours", "Weekly hours", "40, 50 or 60"],
    ["b4_autonomy", "Say over your work", "Tracked tasks to choosing what and how"],
    ["b4_growth", "Growth", "None to promotion track + budget"],
  ];
  // Empty counts as 0; anything else must be a whole number from 0 to 100.
  const value = (k) => { const t = $(`#${k}`).value.trim(); return t === "" ? 0 : /^\d+$/.test(t) && +t <= 100 ? +t : NaN; };
  show("b4", `
    <h2>What mattered</h2>
    <p>Think back to the 10 job comparisons you just completed. You have <b>100 points</b> to distribute across the six features below.
  Allocate more points to features that had a greater influence on
  which job you chose. You can assign zero points to a feature that
  didn't influence your decisions. Your points must add up to
  exactly 100.
</p>
    <div class="points">
      ${rows.map(([k, label, range]) => `<label class="pt"><span class="pt-label"><b>${label}</b><small>${range}</small></span>
        <input id="${k}" type="text" inputmode="numeric" autocomplete="off" placeholder="0"></label>`).join("")}
      <div class="pt total"><span>Points left</span><output id="left">100</output></div>
    </div>`,
  {
    valid: () => {
      const total = rows.map(([k]) => value(k)).reduce((s, v) => s + v, 0);
      const out = $("#left");
      out.textContent = Number.isNaN(total) ? "Whole numbers only" : total > 100 ? `${total - 100} too many` : String(100 - total);
      out.classList.toggle("ok", total === 100);
      return total === 100;
    },
    next: () => { rows.forEach(([k]) => { state.a[k] = value(k); }); background(); },
  });
}

// ---------- 6. background ----------

function withOther(name, options, otherId, placeholder) {
  return radios(name, options) + `<input id="${otherId}" type="text" class="other" maxlength="200" placeholder="${placeholder}" hidden>`;
}

function background() {
  show("background", `
    <h2>About you</h2>
    <fieldset><legend>Your age</legend>${radios("d1", [["18-21", "18–21"], ["22-25", "22–25"], ["26-30", "26–30"], ["31-35", "31–35"], ["36-45", "36–45"], ["46+", "46 or older"]], { inline: true })}</fieldset>
    <fieldset><legend>Your gender</legend>${withOther("d2", [["woman", "Woman"], ["man", "Man"], ["nonbinary", "Non-binary"], ["self", "Prefer to self-describe"], ["na", "Prefer not to say"]], "d2_self", "Self-describe (optional)")}</fieldset>
    <fieldset><legend>Have you ever been granted stock as part of your pay?</legend>${radios("d3", [["esop", "Yes, ESOPs in a private company"], ["rsu", "Yes, RSUs in a listed company"], ["both", "Yes, both"], ["no", "No"], ["unsure", "Not sure"]])}</fieldset>
    <fieldset><legend>How did you hear about this survey?</legend>${withOther("d4", [["placement", "Placement cell / my batch"], ["alumni", "Alumni network"], ["linkedin", "LinkedIn"], ["discord", "A developer Discord or community"], ["friend", "A friend or colleague"], ["other", "Other"]], "d4_other", "Where? (optional)")}</fieldset>`,
  {
    valid: () => {
      $("#d2_self").hidden = checked("d2") !== "self";
      $("#d4_other").hidden = checked("d4") !== "other";
      return ["d1", "d2", "d3", "d4"].every((q) => checked(q));
    },
    next: () => {
      Object.assign(state.a, {
        d1_age: checked("d1"), d2_gender: checked("d2"), d2_self: $("#d2_self").value,
        d3_stock: checked("d3"), d4_channel: checked("d4"), d4_other: $("#d4_other").value,
      });
      if (state.path === "student") student(); else work();
    },
  });
}

function student() {
  show("student", `
    <h2>Your studies</h2>
    <fieldset><legend>Your field</legend>${withOther("st2", [["cs", "Computer science / IT"], ["ece", "Electronics / electrical"], ["other_eng", "Other engineering"], ["other", "Other"]], "st2_other", "Which field? (optional)")}</fieldset>
    <fieldset><legend>Which year are you in?</legend>${radios("st3", [["1", "First"], ["2", "Second"], ["3", "Third"], ["4", "Fourth"], ["5+", "Fifth or later"]], { inline: true })}</fieldset>`,
  {
    valid: () => {
      $("#st2_other").hidden = checked("st2") !== "other";
      return ["st2", "st3"].every((q) => checked(q));
    },
    next: () => {
      Object.assign(state.a, { st2_field: checked("st2"), st2_other: $("#st2_other").value, st3_year: checked("st3") });
      feedback();
    },
  });
}

function work() {
  const was = state.path === "between";
  const job = was ? "your most recent job" : "your current job";
  const hours = () => { const t = $("#j5").value.trim(); const x = Number(t); return t && Number.isFinite(x) && x >= 10 && x <= 100 ? x : null; };
  show("work", `
    <h2>${was ? "Your most recent job" : "Your current job"}</h2>
    <fieldset><legend>Years of full-time work experience</legend>${radios("j1", [["<1", "Less than 1"], ["1-2", "1–2"], ["3-5", "3–5"], ["6-10", "6–10"], ["10+", "More than 10"]], { inline: true })}</fieldset>
    <fieldset><legend>How ${was ? "was your CTC" : "is your CTC"} paid? (closest)</legend>${radios("j3", [["cash", "All as monthly salary"], ["bonus", "Salary + bonus"], ["stock", "Salary + stock (ESOPs or RSUs)"], ["bonus_stock", "Salary + bonus + stock"]])}</fieldset>
    <fieldset><legend>${was ? "Where did you work?" : "Where do you work?"}</legend>${radios("j4", [["onsite", "Fully on-site"], ["hybrid", "Hybrid (some days in office)"], ["remote", "Fully remote"]])}</fieldset>
    <fieldset><legend><label for="j5">About how many hours ${was ? "did" : "do"} you work in a typical week?</label></legend>
      <div class="num"><input id="j5" type="text" inputmode="numeric" autocomplete="off"><span>hours</span></div>
      <p id="j5-msg" class="err"></p></fieldset>
    <fieldset><legend>Which is closest to ${job}? (say over your work)</legend>${radios("j6", Object.entries(LEVELS.autonomy))}</fieldset>
    <fieldset><legend>Which is closest to ${job}? (growth)</legend>${radios("j7", [["none", "No structured learning or promotion path"], ["mentor_budget", "A mentor and/or a learning budget"], ["track", "A clear promotion track"], ["track_plus", "A clear promotion track and a mentor or learning budget"]])}</fieldset>
    <fieldset><legend>Overall, how satisfied ${was ? "were you with your most recent job" : "are you with your current job"}?</legend>
      ${radios("j8", Array.from({ length: 11 }, (_, i) => [String(i), String(i)]), { scale: true })}
      <div class="scale-ends"><span>0 = not at all satisfied</span><span>10 = completely satisfied</span></div></fieldset>`,
  {
    valid: () => {
      const typed = $("#j5").value.trim();
      $("#j5-msg").textContent = typed && hours() === null ? "Please enter a number of hours from 10 to 100." : "";
      return ["j1", "j3", "j4", "j6", "j7", "j8"].every((q) => checked(q)) && hours() !== null;
    },
    next: () => {
      Object.assign(state.a, {
        j1_exp: checked("j1"), j3_paymix: checked("j3"), j4_arrangement: checked("j4"), j5_hours: hours(),
        j6_autonomy: checked("j6"), j7_growth: checked("j7"), j8_satisfaction: Number(checked("j8")),
      });
      feedback();
    },
  });
}

// ---------- 7. submit and end ----------

function feedback() {
  show("feedback", `
    <h2>Last question</h2>
    <label for="e1"><b>Was anything confusing or hard to answer?</b> (optional)</label>
    <textarea id="e1" rows="4" maxlength="2000"></textarea>`,
  { nextLabel: "Submit", next: () => { state.a.e1_text = $("#e1").value; submit(); } });
}

async function submit() {
  const btn = $("#next");
  btn.disabled = true;
  btn.textContent = "Submitting…";
  fail("");
  enter("submit");
  const body = {
    token: state.token, s1: state.s1, anchor_na: state.anchorNA,
    ...(state.anchorNA ? {} : { anchor_ctc: state.S, p2_source: state.p2 }),
    choices: state.choices, ...state.a,
    total_time_s: Math.round((performance.now() - state.t0) / 100) / 10,
    screen_times: state.times,
  };
  try {
    finish((await post("api/submit", body)).code);
  } catch (e) {
    btn.disabled = false;
    btn.textContent = "Try again";
    fail(`Your answers couldn't be sent (${e.message}). Check your connection and try again; nothing is lost while this page stays open.`);
  }
}

function finish(code) {
  window.removeEventListener("beforeunload", guard);
  const link = CFG.shareLink ? `<a href="${esc(CFG.shareLink)}">${esc(CFG.shareLink)}</a>` : ph("shareLink", "LINK");
  show("end", `
    <h2>Thank you, you're done.</h2>
    <p>Your participant code is <b class="code">${esc(code)}</b>. To have your answers deleted, email it to ${ph("contactEmail", "CONTACT EMAIL")} before ${ph("withdrawBy", "WITHDRAW BY")}.</p>
    <p>The job offers were made up, with pay set around ${state.anchorNA ? "a typical CTC" : "the CTC you gave us"}. We're measuring how much people value things like remote work, hours and growth compared with pay. Please don't discuss the questions with anyone who might still take part.</p>
    <p>Know someone eligible? Share this link: ${link}</p>`);
}

document.getElementById("pilot-badge").hidden = !PILOT;
consent();
