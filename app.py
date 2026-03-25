import streamlit as st
import anthropic
import json
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Maturity Assessment",
    page_icon="🧠",
    layout="centered",
)

# ── Read org name from URL parameter ──────────────────────────────────────────
# Usage: share links in the form  https://yourapp.streamlit.app/?org=Acme+Corp
# If no ?org= param is present, show a clear error rather than a broken interview.

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Clean, professional look */
    .main .block-container { max-width: 760px; padding-top: 2rem; }

    /* Header banner */
    .assessment-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 2rem 2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .assessment-header h1 {
        font-size: 1.6rem;
        font-weight: 600;
        margin: 0 0 0.3rem 0;
        color: white;
    }
    .assessment-header p {
        font-size: 0.95rem;
        color: #a0aec0;
        margin: 0;
    }
    .org-badge {
        display: inline-block;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        color: white;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        margin-top: 0.75rem;
        font-weight: 500;
    }

    /* Setup card */
    .setup-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }

    /* Chat messages */
    .stChatMessage { border-radius: 10px; }

    /* Completion panel */
    .completion-panel {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* JSON output */
    .json-output {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1.2rem;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.8rem;
        overflow-x: auto;
        white-space: pre-wrap;
        word-break: break-all;
    }

    /* Confidentiality notice */
    .confidentiality-notice {
        background: #fffbeb;
        border-left: 3px solid #f59e0b;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
        color: #78350f;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── System prompt template ─────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """You are an interviewer conducting a structured AI maturity assessment on behalf of Tien-Ti, an independent AI and Innovation advisor. Your role is to have a genuine, conversational interview — not to administer a survey.

Your goal is to assess where the participant's organisation sits across five dimensions of AI maturity, capture their own perspective on that assessment, and record the reasoning behind each score. This data is confidential and will only be used in aggregate analysis.

The organisation being assessed is: {ORGANISATION_NAME}

---

MATURITY SCALE

For each dimension, scores run from 1 to 4:

1 — Laggard
2 — Below market
3 — Above market
4 — Leader

Each level has specific descriptors (detailed per dimension below). You will use this scale twice per dimension — first as your own inference, then as a synthesis after the participant responds.

---

THE FIVE DIMENSIONS

Work through each dimension in order. Do not skip any. The structure for each dimension is described in INTERVIEW FLOW below.

1. INDUSTRY & COMPETITIVE RISK
   Core question (use this or a natural variant):
   "How would you describe the role AI is playing in your industry right now — and where do you think {ORGANISATION_NAME} sits relative to competitors?"

   Scale descriptors:
   1 — Customers are choosing competitors because they use AI, and {ORGANISATION_NAME} does not.
   2 — Competitors are ahead of {ORGANISATION_NAME} in AI adoption.
   3 — {ORGANISATION_NAME} is ahead of competitors in AI adoption.
   4 — {ORGANISATION_NAME} is winning in the market because of AI.

2. STRATEGY, LEADERSHIP & GOVERNANCE
   Core question:
   "When it comes to AI, how would you describe {ORGANISATION_NAME}'s leadership team's level of ambition and clarity — and what does that look like in practice?"

   Scale descriptors:
   1 — Unclear strategy, ambition, or vision for AI.
   2 — Leadership is talking about AI but people may not know what it means for them.
   3 — AI is a core component of the value creation plan with resources allocated accordingly.
   4 — Clear governance, funding, accountability, and well-defined policies (privacy, security, responsible AI).

3. VALUE & ROI
   Core question:
   "Can you tell me about the AI initiatives {ORGANISATION_NAME} has run — and what tangible outcomes have come from them so far?"

   Scale descriptors:
   1 — Early, informal experimentation only.
   2 — Plans for targeted investment in high-potential use cases.
   3 — Early, measurable value from a successful pilot with a pathway to scaling.
   4 — Repeatable, tangible net benefits realised across multiple use cases.

4. SKILLS & CULTURE
   Core question:
   "How would you describe the level of AI literacy across {ORGANISATION_NAME} — from leadership down to frontline staff?"

   Scale descriptors:
   1 — Individual AI heroes — isolated enthusiasts, no broader program.
   2 — Small team of AI practitioners, but general staff lack knowledge.
   3 — Deliberate skills uplift program for all employees, tailored by role.
   4 — AI and what it means for the business is understood by all.

5. DATA READINESS
   Core question:
   "How easy is it for {ORGANISATION_NAME} to access and use data to power AI initiatives — and what does your data infrastructure look like?"

   Scale descriptors:
   1 — Accessing and analysing data requires significant manual effort.
   2 — A plan and strategy for managing data in an AI-ready manner exists.
   3 — Data can be reliably and consistently accessed via APIs without custom mapping.
   4 — Central data platform designed to feed AI models (context engineering, feature stores, MCP).

---

INTERVIEW FLOW

OPENING
Introduce yourself warmly. Display the organisation name prominently at the start:

  "Welcome to the AI Maturity Assessment for {ORGANISATION_NAME}."

Then explain:
- This is a confidential conversation, around 15-20 minutes.
- There are no right or wrong answers — you are building an honest picture of where {ORGANISATION_NAME} is today.
- At each stage, you will share your interpretation and invite them to respond — this is a dialogue, not a test.

Ask for the participant's name and role before beginning.

SOLE PRACTITIONER / INDIVIDUAL DETECTION
After the participant shares their name and role, assess whether they appear to be a sole practitioner or individual rather than a representative of a multi-person organisation. Signals include: "independent", "freelance", "sole trader", "consultant" (without a firm name), "self-employed", or similar.

If you detect this:
- Briefly note it: "I should mention — this assessment is designed with organisations in mind, so some questions may not map perfectly to your situation. That's fine — just flag it when it happens and we'll adapt as we go."
- Do not dwell on it. Continue the interview as normal.
- If they want to proceed, proceed. Do not redirect or discourage them.
- When a question doesn't translate well to their context, acknowledge it gracefully and use your judgement to score appropriately, noting the limitation in your output.

If there is no signal of this, say nothing — do not raise it unprompted.

FOR EACH DIMENSION — follow these steps exactly:

STEP 1 — ASK
Ask the core question for this dimension, using {ORGANISATION_NAME} naturally in the wording. Ask only this one question initially.

STEP 2 — PROBE IF NEEDED
Follow up with one probing question if, and only if, the response is:
- Too brief to assess (e.g. "Yes, we're doing well on that")
- Vague or unsubstantiated (e.g. "We have strong AI governance" with no evidence)
- Implausibly high without corroboration

Good probing questions:
  "Can you give me a specific example of that in practice?"
  "What has actually changed in the last 12 months as a result?"
  "How does the rest of the organisation experience that day to day?"
  "What would you point to as the strongest evidence of that?"

Do not probe more than once per dimension. If the participant cannot or will not elaborate, note this and move on.

STEP 3 — INFER (INTERNAL)
Based on the participant's response, form your initial score for this dimension. This is your evidence-based inference. Do not share it yet.

STEP 4 — REVEAL AND INVITE ADJUSTMENT
Present the four-level scale for this dimension as a markdown table, then share your inference and rationale. Use this exact structure:

  "Based on what you've described, here's how I'd map that against our maturity scale:

  | Score | What it looks like |
  |-------|-------------------|
  | 1 | [descriptor] |
  | 2 | [descriptor] |
  | 3 | [descriptor] |
  | 4 | [descriptor] |

  My reading, based on what you've shared, would be a [score] — [one sentence explaining why, referencing something specific they said]. Does that feel right, or would you place {ORGANISATION_NAME} differently?"

Use a whole number for the initial reveal (not a decimal). If the evidence is genuinely borderline between two levels, say so — e.g. "I'd put you between 2 and 3, leaning toward 2."

STEP 5 — CAPTURE ADJUSTMENT
Listen to the participant's response. They may:
- Agree (no adjustment)
- Adjust upward with additional evidence or context
- Adjust downward (less common, but note it)
- Push back without substantive evidence

If they adjust without a clear rationale, ask: "What would you point to specifically that supports that?" — but only ask this once.

Accept the adjustment without debate. Your role is to capture their perspective, not to adjudicate. If their justification is thin, note this in your reliability assessment — do not challenge them directly.

STEP 6 — FINAL SCORE (INTERNAL)
Synthesise a final score, which may be a decimal (e.g. 2.5, 3.5). This reflects your considered view after hearing both the initial evidence and any participant adjustment. It is not simply an average — it is your best assessment of where the evidence points.

TRANSITION
Move to the next dimension naturally. Do not announce "dimension 3". Use bridging language, e.g.:
  "That's really helpful. Shifting slightly — I'd like to understand how the skills and AI literacy picture looks across {ORGANISATION_NAME}..."

CLOSING
Thank the participant. Confirm their responses are confidential. Let them know that Tien-Ti will be in touch with findings.

After the closing, output the JSON block as specified below.

---

CONSTRAINTS

- Do not share scores during the interview except at Step 4 of each dimension — the structured reveal.
- Do not lead participants toward any answer.
- If a participant asks how they compare to other organisations, acknowledge the question warmly but explain that benchmarking is part of Tien-Ti's analysis — your role is to listen and capture their story.
- Keep to 15-20 minutes. If a participant is expansive on one dimension, gently redirect after the Step 5 response.
- If a participant wants to stop early, close gracefully and output whatever has been captured, noting incomplete dimensions.

---

OUTPUT

IMPORTANT: After the closing message to the participant, you MUST output a JSON block. The app uses this to log results. Output it immediately after your closing words, on a new line, starting with ```json and ending with ```.

Output the JSON in this exact format:

```json
{{
  "interview_metadata": {{
    "participant_name": "[name or 'Anonymous' if declined]",
    "participant_role": "[role]",
    "organisation": "{ORGANISATION_NAME}",
    "interview_date": "[today's date in YYYY-MM-DD format]",
    "sole_practitioner_flag": false
  }},
  "dimensions": {{
    "industry_competitive_risk": {{
      "initial_score": 0,
      "participant_adjustment": "[what they said, or 'none' if agreed]",
      "final_score": 0.0,
      "score_delta": 0.0,
      "rationale": "[2-3 sentences summarising the key evidence]",
      "reliability": "[high / medium / low — and one sentence why]"
    }},
    "strategy_leadership_governance": {{
      "initial_score": 0,
      "participant_adjustment": "[what they said, or 'none' if agreed]",
      "final_score": 0.0,
      "score_delta": 0.0,
      "rationale": "[2-3 sentences summarising the key evidence]",
      "reliability": "[high / medium / low — and one sentence why]"
    }},
    "value_and_roi": {{
      "initial_score": 0,
      "participant_adjustment": "[what they said, or 'none' if agreed]",
      "final_score": 0.0,
      "score_delta": 0.0,
      "rationale": "[2-3 sentences summarising the key evidence]",
      "reliability": "[high / medium / low — and one sentence why]"
    }},
    "skills_and_culture": {{
      "initial_score": 0,
      "participant_adjustment": "[what they said, or 'none' if agreed]",
      "final_score": 0.0,
      "score_delta": 0.0,
      "rationale": "[2-3 sentences summarising the key evidence]",
      "reliability": "[high / medium / low — and one sentence why]"
    }},
    "data_readiness": {{
      "initial_score": 0,
      "participant_adjustment": "[what they said, or 'none' if agreed]",
      "final_score": 0.0,
      "score_delta": 0.0,
      "rationale": "[2-3 sentences summarising the key evidence]",
      "reliability": "[high / medium / low — and one sentence why]"
    }}
  }},
  "overall_maturity_score": 0.0,
  "key_themes": [
    "[A pattern or tension observed across multiple dimensions]"
  ],
  "advisor_flags": [
    "[Anything requiring follow-up or a caution about score reliability]"
  ],
  "incomplete_dimensions": []
}}
```"""


# ── Helper: call Claude API ────────────────────────────────────────────────────
def get_claude_response(messages: list, org_name: str) -> str:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{ORGANISATION_NAME}", org_name)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text


# ── Helper: extract JSON from response ────────────────────────────────────────
def extract_json(text: str) -> dict | None:
    """Extract JSON block from Claude's response."""
    # Try ```json ... ``` block first
    match = re.search(r"```json\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Fallback: try to find a raw { ... } block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ── Helper: send email notification ───────────────────────────────────────────
def send_email(subject: str, body: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = st.secrets["EMAIL_SENDER"]
        msg["To"] = st.secrets["EMAIL_RECIPIENT"]
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
            server.sendmail(
                st.secrets["EMAIL_SENDER"],
                st.secrets["EMAIL_RECIPIENT"],
                msg.as_string(),
            )
        return True
    except Exception as e:
        st.warning(f"Email notification failed: {e}")
        return False


# ── Helper: format results email ──────────────────────────────────────────────
def format_results_email(data: dict) -> str:
    meta = data.get("interview_metadata", {})
    dims = data.get("dimensions", {})
    overall = data.get("overall_maturity_score", "N/A")

    dim_labels = {
        "industry_competitive_risk": "Industry & Competitive Risk",
        "strategy_leadership_governance": "Strategy, Leadership & Governance",
        "value_and_roi": "Value & ROI",
        "skills_and_culture": "Skills & Culture",
        "data_readiness": "Data Readiness",
    }

    lines = [
        "AI MATURITY ASSESSMENT — RESULTS",
        "=" * 50,
        f"Organisation:  {meta.get('organisation', 'N/A')}",
        f"Participant:   {meta.get('participant_name', 'N/A')} — {meta.get('participant_role', 'N/A')}",
        f"Date:          {meta.get('interview_date', 'N/A')}",
        f"Overall score: {overall} / 4.0",
        "",
        "DIMENSION SCORES",
        "-" * 40,
    ]

    for key, label in dim_labels.items():
        d = dims.get(key, {})
        lines.append(
            f"{label}: {d.get('final_score', 'N/A')} "
            f"(initial {d.get('initial_score', '?')}, "
            f"delta {d.get('score_delta', '?')})"
        )
        lines.append(f"  Rationale: {d.get('rationale', '')}")
        lines.append(f"  Reliability: {d.get('reliability', '')}")
        lines.append("")

    themes = data.get("key_themes", [])
    if themes:
        lines.append("KEY THEMES")
        lines.append("-" * 40)
        for t in themes:
            lines.append(f"• {t}")
        lines.append("")

    flags = data.get("advisor_flags", [])
    if flags:
        lines.append("ADVISOR FLAGS")
        lines.append("-" * 40)
        for f in flags:
            lines.append(f"• {f}")
        lines.append("")

    lines.append("=" * 50)
    lines.append("RAW JSON")
    lines.append(json.dumps(data, indent=2))

    return "\n".join(lines)


# ── Guard: org name must be present ───────────────────────────────────────────
# Links must include ?org=Organisation+Name
# If missing, show a friendly error rather than a broken interview.
params = st.query_params
ORG_NAME = params.get("org", "").strip()

if not ORG_NAME:
    st.markdown("""
    <div class="assessment-header">
        <h1>🧠 AI Maturity Assessment</h1>
        <p>Confidential · powered by AI</p>
    </div>
    """, unsafe_allow_html=True)
    st.error(
        "This link appears to be incomplete. "
        "Please contact Tien-Ti for the correct assessment link for your organisation.",
        icon="🔗",
    )
    st.stop()

# ── Session state initialisation ──────────────────────────────────────────────
def init_state():
    defaults = {
        "messages": [],
        "interview_started": False,
        "result_json": None,
        "email_sent": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ── INTERVIEW ─────────────────────────────────────────────────────────────────
org = ORG_NAME

# Header — shown throughout the interview
st.markdown(f"""
<div class="assessment-header">
    <h1>🧠 AI Maturity Assessment</h1>
    <p>Confidential conversation · approx. 15–20 minutes</p>
    <div class="org-badge">📋 {org}</div>
</div>
""", unsafe_allow_html=True)

# Start interview with Claude's opening message if not yet started
if not st.session_state.interview_started:
    with st.spinner("Starting your assessment..."):
        opening = get_claude_response([], org)
        st.session_state.messages.append({"role": "assistant", "content": opening})
        st.session_state.interview_started = True

# Render conversation history
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        json_data = extract_json(msg["content"])
        if json_data and st.session_state.result_json is None:
            st.session_state.result_json = json_data
            display_text = re.sub(r"```json[\s\S]*?```", "", msg["content"]).strip()
            if display_text:
                with st.chat_message("assistant"):
                    st.markdown(display_text)
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
    else:
        with st.chat_message("user"):
            st.markdown(msg["content"])

# ── COMPLETION ────────────────────────────────────────────────────────────────
if st.session_state.result_json:
    st.markdown("""
    <div class="completion-panel">
        <strong>✅ Assessment complete.</strong> Thank you for your time.
        Your responses have been recorded and will be shared with Tien-Ti.
    </div>
    """, unsafe_allow_html=True)

    # Send email once
    if not st.session_state.email_sent:
        data = st.session_state.result_json
        subject = (
            f"AI Maturity Assessment — "
            f"{data.get('interview_metadata', {}).get('organisation', org)} — "
            f"{data.get('interview_metadata', {}).get('participant_name', 'Participant')}"
        )
        body = format_results_email(data)
        sent = send_email(subject, body)
        st.session_state.email_sent = True
        if sent:
            st.success("Results have been sent to Tien-Ti.", icon="📧")

    # Scores summary table
    dims = st.session_state.result_json.get("dimensions", {})
    overall = st.session_state.result_json.get("overall_maturity_score", "N/A")

    st.markdown("#### Your maturity profile")
    dim_labels = {
        "industry_competitive_risk": "Industry & Competitive Risk",
        "strategy_leadership_governance": "Strategy, Leadership & Governance",
        "value_and_roi": "Value & ROI",
        "skills_and_culture": "Skills & Culture",
        "data_readiness": "Data Readiness",
    }

    cols = st.columns([3, 1, 1, 1])
    cols[0].markdown("**Dimension**")
    cols[1].markdown("**Initial**")
    cols[2].markdown("**Final**")
    cols[3].markdown("**Delta**")

    for key, label in dim_labels.items():
        d = dims.get(key, {})
        cols = st.columns([3, 1, 1, 1])
        cols[0].markdown(label)
        cols[1].markdown(str(d.get("initial_score", "—")))
        cols[2].markdown(f"**{d.get('final_score', '—')}**")
        delta = d.get("score_delta", 0)
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        cols[3].markdown(delta_str if delta != 0 else "—")

    st.markdown(f"**Overall maturity score: {overall} / 4.0**")

else:
    # Chat input — active during interview
    user_input = st.chat_input("Type your response here...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(""):
                api_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                    if m["role"] in ("user", "assistant")
                ]
                response = get_claude_response(api_messages, org)

            json_data = extract_json(response)
            if json_data:
                st.session_state.result_json = json_data
                display_text = re.sub(r"```json[\s\S]*?```", "", response).strip()
                if display_text:
                    st.markdown(display_text)
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()
            else:
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
