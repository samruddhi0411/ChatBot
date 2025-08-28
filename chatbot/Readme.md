# SmartAgent

FastAPI + OpenAI tool-calling chatbot with three tools: calc, time_in_timezone, web_search.  
Live demo friendly. Lightweight. No DB.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your OPENAI_API_KEY
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
