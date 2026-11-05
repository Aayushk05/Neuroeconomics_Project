# Survey copy — Arm A, draft v2

Draft v1 was written on 28 Oct 2026. v2 (2 Nov) shortens it after the first test run, which took 5.9 minutes; the cuts and their reasons are item 13 in section 10. Participant-facing text is in quote blocks; everything else is a note for us or for the build.

Files that go with this:

- `survey/design_blocks.csv` — the 24 design pairs (3 blocks × 8), frozen from the validated simulation. Salary is stored as a multiplier of the participant's own CTC (0.8 / 1.0 / 1.25).
- `survey/attention_checks.csv` — the two fixed check pairs (screens 4 and 9).

**Fill in before the pilot:** `[COURSE]`, `[INSTRUCTOR]`, `[CONTACT EMAIL]`, `[ETHICS LINE]`, `[PAYMENT]`, `[STORAGE]`, `[DELETE BY]`, `[WITHDRAW BY]`, `[LINK]`.

Section 10 lists every change from the locked spec. Those need to go into the pre-registration before the pilot.

---

## Flow and timing

| # | Section | Shown to | First test run (v1) | v2 estimate |
| --- | --- | --- | --- | --- |
| 0 | Consent | everyone | 0:21 (skimmed) | 0:35 |
| 1–2 | Screener (S1) and pay anchor (P1–P2) | everyone / eligible | 0:30 | 0:25 |
| 3 | Instructions | eligible | 0:06 (skimmed) | 0:25 |
| 4 | 10 choice screens: 8 design + checks at screens 4 and 9 | eligible | 2:26 | 2:00 |
| 5 | B1 Money now or later | eligible | 0:37 | 0:30 |
| 6 | B2 A sure amount or shares | eligible | 0:24 | 0:20 |
| 7 | B3 Two worlds (1 item) | eligible | 0:28 (2 items) | 0:12 |
| 8 | B4 100 points | eligible | 1:02 | 0:45 |
| 9 | Background (D items + ST or J items) | eligible | 0:19 | 0:40 |
| 10 | Feedback + end screen | eligible | 0:02 | 0:05 |

The v1 test run was by a student who wrote the survey, so consent and instructions were skimmed and the student page is shorter than the working-professional one. v2 should take a first-time participant about 7 minutes. The app records time on every screen, so the pilot will give the real figure.

---

## 0. Consent page

> **Job choices study**
>
> We're Prajna Penmetsa and Aayush Khatanhar, students at IIIT Hyderabad. This survey, on how people in tech choose between job offers, is part of our course project for [COURSE], supervised by [INSTRUCTOR].
>
> - **About 7 minutes.** Pick between 10 pairs of made-up job offers, then answer a few short questions, including your pay.
> - **Who can take part:** anyone 18 or older who is a student or works in a tech role.
> - **Voluntary.** Close the page at any time; unfinished answers are thrown away.
> - **Anonymous.** We don't ask your name, email or employer, or store your IP address with your answers. Results are only reported as group averages.
> - **Your data** is stored [STORAGE], seen only by the two of us [and course staff], used for our course presentation and report, and deleted by [DELETE BY].
> - **Changing your mind.** You'll get a code at the end. Email it to [CONTACT EMAIL] before [WITHDRAW BY] and we'll delete your answers. Questions go to the same address.
> - **Risks and payment.** None beyond everyday life; you can choose not to give your pay. [PAYMENT, e.g. "There is no payment for taking part."]
>
> [ETHICS LINE: approval or exemption reference. Ask the TA what the course requires.]
>
> ☐ I'm 18 or older, I've read the above, and I agree to take part.
>
> **[Start]** (disabled until the box is ticked)

---

## 1. Screener

> **S1. Which best describes you right now?**
> - I'm a student (undergraduate)
> - I'm a student (Master's or PhD)
> - I work full-time in a tech role (software, data, IT, hardware, product, design, etc.)
> - I'm between jobs, and my last job was in a tech role
> - I work full-time in a non-tech role
> - None of these

Routing:

- The two student options go to the **student path**. Interns count as students.
- Full-time tech goes to the **professional path**.
- Between jobs goes to the **professional path**, worded for their last job.
- Non-tech or none of these goes to **screen-out**.

Students from any field are kept. Field is recorded (ST2) so the analysis can restrict to tech fields if needed.

Screen-out text:

> Thanks for your interest. This study is for students and people working in tech, so that's the end of the survey for you. Nothing you entered has been saved.

---

## 2. Pay anchor

This screen sets S, the base for all CTC figures in the choice screens and in B3 and B4.

> We only use this to set realistic pay in the offers.

> **P1 (working full-time).** What's your current total CTC per year, in LPA? Include bonus and stock; a best guess is fine.
>
> **P1 (between jobs).** What was the total CTC per year of your last job, in LPA? Include bonus and stock; a best guess is fine.
>
> **P1 (student).** What total CTC per year do you have, or expect, for your first full-time job, in LPA?
>
> [ number ] LPA  ☐ Prefer not to say

> **P2 (students only; skip if P1 = prefer not to say).** Is that an actual offer, or your estimate?
> - I have this offer
> - It's my estimate

Validation (number, step 0.1, allowed range 1–200):

- Above 200: "That looks like rupees rather than lakhs. For example, enter 12 for ₹12,00,000 a year."
- Below 1: "Please enter your CTC in lakhs per year. For example, enter 4.5 for ₹4,50,000."

If the participant picks "Prefer not to say", use S = 12 and record `anchor_type = default`. They aren't told the number; the instructions and end screen say pay is set "around a typical CTC" instead of "around the pay you told us". In the analysis, run everything with and without these people.

---

## 3. Instructions screen

Only what isn't obvious from the choice screens themselves is explained here.

> **How this part works**
>
> You'll see **10 pairs of job offers**. Pick the one you'd accept. Both are full-time jobs in your field and city, identical except for the six features shown.
>
> - **Total CTC** is yearly pay before tax, set around the pay you told us. It's the same whatever the hours.
> - **Year-end bonus** is guaranteed, not linked to performance.
> - **ESOPs** are stock options in a private company. They can only be cashed if it's sold or goes public, which may never happen.
>
> There are no right or wrong answers, and you can't go back.
>
> **[Start]**

---

## 4. Choice screens (10)

### 4.1 Screen template

> **Offer {n} of 10**
>
> Which job would you accept?
>
> |  | **Job A** | **Job B** |
> | --- | --- | --- |
> | Total CTC | ₹{ctc_A} LPA | ₹{ctc_B} LPA |
> | How it's paid | {varpay_A} | {varpay_B} |
> | Where you work | {arrangement_A} | {arrangement_B} |
> | Weekly hours | {hours_A} | {hours_B} |
> | Say over your work | {autonomy_A} | {autonomy_B} |
> | Growth | {growth_A} | {growth_B} |
>
> **[Accept Job A]**  **[Accept Job B]**

The row order is the same for everyone and on every screen. One answer is required, and there's no back button.

### 4.2 Level wording

The codes match `analysis/pipeline.py` and `design_blocks.csv`. Labels are kept short because each participant reads them on 10 screens; the instructions define the bonus and ESOPs.

| Attribute | Code | Text on screen |
| --- | --- | --- |
| salary_level | 0.8 / 1.0 / 1.25 | ₹{round(level × S, 1)} LPA |
| varpay | cash | All monthly salary |
|  | bonus | 80% salary + 20% year-end bonus |
|  | equity | 80% salary + 20% ESOPs (4-year vest) |
| arrangement | onsite | On-site, 5 days a week |
|  | hybrid | Hybrid, 2–3 office days a week |
|  | remote | Fully remote |
| hours | 40 / 50 / 60 | 40 hours / 50 hours / 60 hours |
| autonomy | assigned | Tasks assigned and closely tracked |
|  | some | Tasks assigned; some say in how |
|  | choose | You choose what and how |
| growth | none | No learning support or promotion track |
|  | mentorship | Mentor + learning budget |
|  | track | Promotion track + learning budget |

**CTC display rule.** Show round(level × S, 1), dropping a trailing ".0". For example, S = 12 shows ₹9.6, ₹12 and ₹15 LPA. The export stores the number exactly as displayed.

The varpay levels hold total CTC fixed. Only the form of 20% of it changes, which is what H3 needs ("below cash of equal nominal amount"). The bonus is guaranteed and deferred, so it lines up with B1 (delay). The ESOPs are risky and illiquid, so they line up with B2 (risk).

### 4.3 Attention checks (screens 4 and 9)

| Screen | Job A (left) | Job B (right) |
| --- | --- | --- |
| 4 | **better**: 1.25 × S · all monthly salary · hybrid · 40 hours · you choose what and how · promotion track + learning budget | worse: 0.8 × S · all monthly salary · hybrid · 60 hours · tasks assigned and closely tracked · no learning support or promotion track |
| 9 | worse: 0.8 × S · year-end bonus · fully remote · 60 hours · tasks assigned and closely tracked · no learning support or promotion track | **better**: 1.25 × S · year-end bonus · fully remote · 40 hours · you choose what and how · promotion track + learning budget |

How the checks are built. Re-read the brief's "already fixed" list before changing any of this.

- **Brief fix 3.** Varpay and arrangement are identical within each pair. The better job is strictly better on all four unambiguous attributes (CTC, hours, autonomy, growth), by the full range of each.
- **Growth contrast.** It is track vs none, not track vs mentorship. Some people genuinely rank mentorship above a promotion track.
- **Brief fix 2.** "Better" means preference direction, not level order. Here that only affects how the pairs were picked, since varpay is held equal.
- **Position.** The better job is on the left at screen 4 and on the right at screen 9. Anyone who clicks the same side every time fails exactly one check.
- **Scoring (brief fix 4, unchanged).** A check is failed if the worse job is chosen. Failing either check means exclusion. The floor of 100 counts participants retained after exclusions.
- **Appearance.** Same look and wording as every other screen. Never labelled as a check.

### 4.4 Order and randomisation

- **Block.** Each participant gets one of the 3 blocks in `design_blocks.csv`, assigned when they leave the pay-anchor screen. Pick the block with the fewest completed responses plus starts in the last 30 minutes, breaking ties at random. Counting recent starts stops a burst of people who start together from all landing in one block; older abandoned starts don't count, so dropouts don't unbalance the blocks.
- **Screen order.** The block's 8 design pairs go on screens 1–3, 5–8 and 10, shuffled per participant. Screens 4 and 9 are always the checks.
- **Left/right.** For each design pair, randomly flip which profile is shown as Job A, and record the flip. Checks are never flipped.

---

## 5. Add-on blocks

### B1 — Money now or later

> **Money now or later**
>
> Imaginary money from here on. Your employer owes you a one-time payment: **₹2,00,000 today**, or more **in 12 months**. Both are guaranteed.
>
> | Row | Today | In 12 months |
> | --- | --- | --- |
> | 1 | ₹2,00,000 | ₹2,10,000 |
> | 2 | ₹2,00,000 | ₹2,20,000 |
> | 3 | ₹2,00,000 | ₹2,40,000 |
> | 4 | ₹2,00,000 | ₹2,70,000 |
> | 5 | ₹2,00,000 | ₹3,00,000 |
>
> **From which row would you wait?**
> ○ Row 1 ○ Row 2 ○ Row 3 ○ Row 4 ○ Row 5 ○ None — I'd take ₹2,00,000 today in every row

A single radio answer is a single switch point by construction, so multiple switching can't happen. Record `b1_switch` ∈ {1–5, none}.

With one 12-month delay, k equals the premium needed to wait:

| b1_switch | 1 | 2 | 3 | 4 | 5 | none |
| --- | --- | --- | --- | --- | --- | --- |
| k interval | ≤ 0.05 | 0.05–0.10 | 0.10–0.20 | 0.20–0.35 | 0.35–0.50 | > 0.50 |

A single delay gives one discount rate per person. It can't tell hyperbolic from exponential discounting, so report it as "k (one delay)". Treat it as interval-censored.

### B2 — A sure amount or shares

> **A sure amount or shares**
>
> A one-time grant from your employer: **₹2,00,000 for sure**, or **shares** that turn out to be worth ₹4,00,000 or nothing. You find out straight away.
>
> | Row | For sure | Chance the shares pay ₹4,00,000 |
> | --- | --- | --- |
> | 1 | ₹2,00,000 | 30% (3 in 10) |
> | 2 | ₹2,00,000 | 50% (5 in 10) |
> | 3 | ₹2,00,000 | 65% (about 2 in 3) |
> | 4 | ₹2,00,000 | 80% (8 in 10) |
> | 5 | ₹2,00,000 | 95% (19 in 20) |
>
> **From which row would you take the shares?**
> ○ Row 1 ○ Row 2 ○ Row 3 ○ Row 4 ○ Row 5 ○ None — I'd take ₹2,00,000 for sure in every row

This elicits a **probability equivalent** p*, not a certainty equivalent: the sure amount is fixed and the probability varies. The gamble resolves immediately, so B2 measures risk without delay, and B1 covers delay. A risk-neutral person switches at row 2.

| b2_switch | 1 | 2 | 3 | 4 | 5 | none |
| --- | --- | --- | --- | --- | --- | --- |
| p* interval | ≤ 30% | 30–50% | 50–65% | 65–80% | 80–95% | > 95% |

### B3 — Two worlds

A Solnick & Hemenway style item. The amounts are scaled to the participant's own CTC (S). Randomise which world is listed first and record it.

> **Two worlds**
>
> Prices are the same in both worlds. Which would you rather live in?
> - You earn ₹{S} LPA a year. Other people in your field earn ₹{S/2} LPA on average.
> - You earn ₹{2S} LPA a year. Other people in your field earn ₹{4S} LPA on average.

Round the amounts the same way as the CTC display rule. **H5** reads off this item: choosing the first world, with lower absolute but higher relative pay, is the positional choice. The answer is exported as `b3a_choice` / `b3a_order`, unchanged from v1. v1 also had a paid-leave item (B3b) as a domain contrast; it was cut in v2 because no hypothesis uses it.

### B4 — What mattered (100 points)

> **What mattered**
>
> Split **100 points** across the six features by how much each mattered in your choices, within the ranges you saw.
>
> | Feature | Range | Points |
> | --- | --- | --- |
> | Total CTC | ₹{0.8S} to ₹{1.25S} LPA | [  ] |
> | How it's paid | All salary, or 20% as bonus or ESOPs | [  ] |
> | Where you work | On-site, hybrid or remote | [  ] |
> | Weekly hours | 40, 50 or 60 | [  ] |
> | Say over your work | Tracked tasks to choosing what and how | [  ] |
> | Growth | None to promotion track + budget | [  ] |
> | | **Points left** | **{100 − total}** |
>
> **[Next]** (enabled only when the total is exactly 100)

- **UI.** Six number boxes (0–100) and a live "points left" counter, which shows "N too many" if the total goes over. Don't auto-rebalance the other boxes when one changes, because that anchors people. In the v1 test run this was the slowest page (62 s); counting down to zero is quicker than adding up to 100.
- **Labels for H4.** The labels are exactly the six conjoint attributes, so H4 compares like with like.
- **Ranges.** They are shown because a conjoint attribute's revealed importance depends on the range of levels. With the pivot, CTC only varies ±20–25%, so stated and revealed weights are comparable only if people allocate points over the same ranges.

---

## 6. Background

### D — Everyone

> **D1. Your age**
> 18–21 · 22–25 · 26–30 · 31–35 · 36–45 · 46 or older

> **D2. Your gender**
> Woman · Man · Non-binary · Prefer to self-describe: [   ] · Prefer not to say

> **D3. Have you ever been granted stock as part of your pay?**
> Yes, ESOPs in a private company · Yes, RSUs in a listed company · Yes, both · No · Not sure

> **D4. How did you hear about this survey?**
> Placement cell / my batch · Alumni network · LinkedIn · A developer Discord or community · A friend or colleague · Other: [   ]

D3 is a moderator for H3: listed RSUs are close to cash. D4 describes the sample and lets us check for channel effects.

### ST — Students

> **ST2. Your field**
> Computer science / IT · Electronics / electrical · Other engineering · Other: [   ]

> **ST3. Which year are you in?**
> First · Second · Third · Fourth · Fifth or later

ST1 (degree) was cut in v2: S1 already separates undergraduates from Master's and PhD students.

### J — Working (and between jobs: "your most recent job")

> **J1. Years of full-time work experience**
> Less than 1 · 1–2 · 3–5 · 6–10 · More than 10

> **J3. How is your CTC paid?** (closest)
> All as monthly salary · Salary + bonus · Salary + stock (ESOPs or RSUs) · Salary + bonus + stock

> **J4. Where do you work?**
> Fully on-site · Hybrid (some days in office) · Fully remote

> **J5. About how many hours do you work in a typical week?** [ number ] hours (allowed 10–100)

> **J6. Which is closest to your current job? (say over your work)**
> Tasks assigned and closely tracked · Tasks assigned; some say in how · You choose what and how

> **J7. Which is closest to your current job? (growth)**
> No structured learning or promotion path · A mentor and/or a learning budget · A clear promotion track · A clear promotion track and a mentor or learning budget

> **J8. Overall, how satisfied are you with your current job?**
> 0 (not at all satisfied) … 10 (completely satisfied)

J2 (company type) was cut in v2; it was descriptive only. Item numbers are kept so they match the export columns.

The J items let H6 run inside Arm A. Map each current job onto the conjoint levels, apply the estimated part-worths plus β_ln × ln(CTC), and test whether that index beats ln(CTC) alone at predicting J8, with k-fold cross-validation. Mapping:

- **J3:** salary only → cash; + bonus → bonus; any stock → equity.
- **J5:** piecewise-linear between the 40/50/60 part-worths, clamped outside that range.
- **J7:** mentor/budget → mentorship; any promotion track → track.

**Aayush:** if the Stack Overflow 2025 satisfaction item uses different wording or a different scale, swap J8 for it so the outcome matches in both arms.

### Optional, everyone

> **E1. Was anything confusing or hard to answer?** (optional) [ text ]

---

## 7. End screen

> **Thank you, you're done.**
>
> Your participant code is **{code}**. To have your answers deleted, email it to [CONTACT EMAIL] before [WITHDRAW BY].
>
> The job offers were made up, with pay set around the CTC you gave us. We're measuring how much people value things like remote work, hours and growth compared with pay. Please don't discuss the questions with anyone who might still take part.
>
> Know someone eligible? Share this link: [LINK]

`{code}` is a random 6-character string stored with the response. It is separate from `pid`.

---

## 8. Build notes

These are rules the instrument must follow.

- **No back button.** Every choice screen requires an answer.
- **Timing.** Record time on every screen in milliseconds. This is descriptive only; the exclusion rule stays "fail either check".
- **Saving.** Save a response only on final submit, as the consent page promises. Keep nothing but a count of started-but-unfinished sessions, for the dropout rate.
- **IP addresses.** Don't store IPs with responses. Host access logs are separate, so don't claim more than the consent page says.
- **Mobile.** Most LinkedIn and Discord traffic will be on phones, so the choice table must fit a phone screen without sideways scrolling. Test this in the pilot.
- **Pilot data.** Pilot runs use the survey link with `?pilot=1`; those responses export to separate `*_pilot.csv` files. Don't pool them with the main data if anything changes after the pilot.

---

## 9. Export format

**`choices_long.csv`** has one row per job per screen per participant. It keeps the columns of `simulated_choices.csv` (`pid`, `set_id`, `alt_id`, `chosen`, the six attributes, `kind`) and adds new ones:

| Column | Meaning |
| --- | --- |
| `pid` | Participant id |
| `block` | 0, 1 or 2 |
| `set_id` | Screen number, 1–10 |
| `kind` | `design` or `check` |
| `pair` | 1–8 for design screens (row in `design_blocks.csv`), blank for checks |
| `alt_id` | 1 = Job A (left), 2 = Job B (right) |
| `flipped` | 1 if the design pair was shown in reverse order |
| `chosen` | 1 if this job was chosen |
| `salary_level` | 0.8, 1.0 or 1.25 |
| `salary` | CTC shown on screen, in LPA |
| `varpay`, `arrangement`, `hours`, `autonomy`, `growth` | Codes as in 4.2 |
| `rt_ms` | Time on screen |

**`participants.csv`** has one row per participant. Columns: `pid`, `code`, `path` (student / professional / between jobs), `anchor_ctc`, `anchor_type` (current / most recent / offer / estimate / default), `block`, `b1_switch`, `b2_switch`, `b3a_choice`, `b3a_order`, the six `b4_*` points, the D, ST and J answers, `e1_text`, `total_time_s`, `screen_times`, `submitted_at`.

**Pipeline changes (done 29 Oct, in `analysis/pipeline.py`):**

- Salary dummies are coded from `salary_level`: `sal_100` (1.0×) and `sal_125` (1.25×) against 0.8×.
- `BETTER["salary"]` becomes `[0.8, 1.0, 1.25]`.
- The WTP model uses ln(salary).
- New H1 test (see section 10).
- Standard errors clustered by `pid`.
- Add a position term on `alt_id`.

---

## 10. Changes from the locked spec

Record these in the pre-registration before the pilot.

1. **Salary levels.** Changed from fixed ₹5 / 12 / 25 LPA to 0.8 / 1.0 / 1.25 × the participant's own CTC (P1). The label is now "Total CTC".
   - *Why:* with H2-sized preferences, the fixed levels let salary decide about 99% of choices. Remote WTP couldn't be detected (13–39% power across the 5–15% range), while the pivot gives 77–100%.
2. **H1 test.** Becomes a between-person test. Fit a conditional logit with both ln(CTC) and CTC (₹ lakh), with standard errors clustered by participant. H1 is supported if the ln(CTC) coefficient is > 0, one-sided α = .05. Robustness: the same test among working professionals only.
   - *Note:* in simulation this test was somewhat liberal (12% false positives at a nominal 5%), so also report a participant-level bootstrap p-value.
3. **H2 metric.** WTP as a share of own CTC = exp(β_k / β_ln) − 1, from the ln(CTC) model. The prediction is unchanged: remote at 5–15%.
4. **Variable pay wording.** Total CTC is held fixed and 20% of it changes form. The bonus is guaranteed and paid at year end; equity is ESOPs in a private company with a 4-year vest. H3 links the bonus gap to B1 (delay) and the equity gap to B2 (risk).
5. **B2 is a probability equivalent,** not a certainty equivalent. The gamble resolves immediately.
6. **B1 reports k for a single 12-month delay.** It doesn't claim hyperbolic discounting.
7. **B3.** One item, with amounts scaled to own CTC and the order randomised. The paid-leave item was dropped (see 13).
8. **B4.** The labels are the six conjoint attributes, with their level ranges shown.
9. **H6 adds an Arm A test.** It uses working professionals' current-job items (J3–J7) and satisfaction (J8). This is independent of the 30 Oct decision on Arm B proxies.
10. **Attention checks.** Two fixed pairs with the widest gap. The better job is on the left at screen 4 and on the right at screen 9. The exclusion rule is unchanged (fail either check), and the floor of 100 refers to retained participants.
11. **Screens.** 1 instruction screen + 10 choice screens (8 design + 2 checks); the old "nine screens" figure is out of date. The design pair order is shuffled per participant and the left/right position is randomised, with a position term in the model.
12. **New covariates.** Pay anchor (P1–P2), ESOP/RSU experience (D3), recruitment channel (D4), and current-job items for professionals (J1, J3–J8).
13. **Shortened survey (v2, 2 Nov).** The first test run took 5.9 minutes with the consent and instructions skimmed. v2 roughly halves the consent and instructions, shortens the level labels on the choice screens, and drops three items no hypothesis uses: the paid-leave item (B3b), degree (ST1) and company type (J2). Every hypothesis keeps its measure. Target: about 7 minutes for a first-time participant.
