# Greg Dougall — Personal Project Studio

A small Flask site for gregdougall.com. It presents Greg's practical work and includes a production contact endpoint that delivers messages through Resend.

## Current structure

- `index.html` — semantic homepage content
- `static/css/styles.css` — responsive layout and visual design
- `static/js/main.js` — accessible mobile navigation and current footer year
- `app.py` — Flask routes and the server-side contact endpoint
- `requirements.txt` / `Procfile` — Railway runtime configuration

## AI Corral

`POST /api/ai-corral` accepts one JSON prompt of up to 600 characters and sends it to the OpenAI Responses API. The model must return a strict structured result containing an answer, category, confidence, and the rule followed. The server validates every field and length before returning approved data to the browser. A structurally invalid result receives at most one correction attempt; provider failures are not retried.

AI Corral uses no tools, browsing, files, external actions, conversation history, background work, or persistence. It reuses the site's conservative in-memory request throttle, and prompts and responses are not stored by this application.

## Preview locally

Install the Python dependencies, configure the contact variables, and run Flask:

```powershell
cd "C:\Project GregDougall"
python -m pip install -r requirements.txt
$env:RESEND_API_KEY="your-resend-api-key"
$env:CONTACT_TO_EMAIL="private-destination@example.com"
$env:CONTACT_FROM_EMAIL="verified-sender@example.com"
$env:CONTACT_FROM_NAME="Greg Dougall Website"
$env:OPENAI_API_KEY="your-openai-api-key"
$env:AI_CORRAL_MODEL="gpt-5.6-luna"
python app.py
```

Then visit `http://localhost:8000` and stop the server with `Ctrl+C`. Keep real values in local environment variables or Railway Variables; do not commit them.

## Planned future work

- Project case-study pages
- Ask My Projects
- Resume page
- Deployment to gregdougall.com
