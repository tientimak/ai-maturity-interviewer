# AI Maturity Interviewer

A conversational AI tool that conducts structured AI maturity assessments with participants from client organisations. Built with Streamlit and Claude.

## What it does

- Conducts a 15–20 minute guided conversation covering five dimensions of AI maturity
- Scores each dimension on a 1–4 scale, with Claude's initial inference and participant adjustment
- Captures three data points per dimension: initial score, participant adjustment, final score
- Emails a structured results summary to Tien-Ti on completion
- Designed for use with multiple participants across a client organisation

## The five dimensions

1. Industry & Competitive Risk
2. Strategy, Leadership & Governance
3. Value & ROI
4. Skills & Culture
5. Data Readiness

## Setup

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Configure secrets
Create `.streamlit/secrets.toml` (this file is gitignored — never commit it):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
EMAIL_SENDER = "your-gmail@gmail.com"
EMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # Gmail App Password
EMAIL_RECIPIENT = "tientimak@live.com"
```

### 3. Run locally
```
streamlit run app.py
```

## Deploying

Push to GitHub, then deploy via [share.streamlit.io](https://share.streamlit.io). Add secrets under Advanced Settings before deploying.

## Usage

Share the app URL with participants. Before the interview begins, the participant enters their organisation name — this is used throughout the conversation and in the results output.

## Data

Results are emailed to Tien-Ti at the end of each interview as a structured text summary with the full JSON appended. The JSON contains all scores, rationale, score deltas, and advisor flags.

## Cost

Each interview uses approximately 4,000–8,000 tokens with claude-sonnet-4-5. At current Anthropic pricing, a cohort of 20 participants costs less than $2 in API usage.
