# src/agent.py
import json
from typing import List, Dict, Any

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError

from src.settings import settings
from src.tools import TOOL_SPECS, TOOL_FUNCS

SYSTEM_PROMPT = """You are SmartAgent, a helpful assistant.
Prefer calling tools for arithmetic and current time.
For Indian cities like Mumbai/Delhi/Chennai/Bengaluru, use Asia/Kolkata.
Use tools when they help. Be concise. If a timezone is ambiguous, suggest a valid IANA zone.
If a tool returns 'error:', explain it briefly and suggest a fix.
"""

def _to_gemini_function_declarations(tool_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    funcs = []
    for t in tool_specs:
        f = t.get("function", {})
        funcs.append({
            "name": f.get("name"),
            "description": f.get("description", ""),
            "parameters": f.get("parameters", {}),
        })
    return funcs

def _history_to_contents(history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    contents = []
    for m in history:
        role = m.get("role")
        text = m.get("content") or ""
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": text}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
    return contents

def _extract_function_calls(resp) -> List[Dict[str, Any]]:
    """
    Returns a list of {"name": str, "args": dict} for each function call part.
    """
    calls = []
    try:
        cands = getattr(resp, "candidates", []) or []
        if not cands:
            return calls
        content = getattr(cands[0], "content", None)
        parts = getattr(content, "parts", None) if content is not None else None
        if not parts:
            return calls
        for p in parts:
            fc = (
                getattr(p, "function_call", None)
                or getattr(p, "functionCall", None)
                or (p.get("functionCall") if isinstance(p, dict) else None)
                or (p.get("function_call") if isinstance(p, dict) else None)
            )
            if not fc:
                continue
            name = getattr(fc, "name", None) if not isinstance(fc, dict) else fc.get("name")
            raw_args = getattr(fc, "args", None) if not isinstance(fc, dict) else fc.get("args", {})
            try:
                if hasattr(raw_args, "to_dict"):
                    raw_args = raw_args.to_dict()
            except Exception:
                pass
            if isinstance(raw_args, str):
                try:
                    raw_args = json.loads(raw_args)
                except Exception:
                    raw_args = {}
            if raw_args is None:
                raw_args = {}
            calls.append({"name": name, "args": raw_args})
    except Exception:
        pass
    return calls

def _final_text(resp) -> str:
    try:
        return resp.text or ""
    except Exception:
        try:
            cands = getattr(resp, "candidates", [])
            if cands and cands[0].content and cands[0].content.parts:
                texts = [getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
                         for p in cands[0].content.parts]
                texts = [t for t in texts if t]
                return "\n".join(texts)
        except Exception:
            pass
    return ""

def run_agent(user_message: str, history: List[Dict]) -> Dict:
    """
    Takes the latest user_message and prior chat history, runs tool-call loop until final reply is produced.
    Returns {"reply": str, "history": updated_history}
    """
    # Keep a working copy so we can return full history including user turns
    history = list(history)
    history.append({"role": "user", "content": user_message})

    # Configure Gemini
    genai.configure(api_key=settings.google_api_key)
    function_declarations = _to_gemini_function_declarations(TOOL_SPECS)

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SYSTEM_PROMPT,
        tools=[{"function_declarations": function_declarations}],
    )

    # Build contents from full history (includes this turn's user message)
    contents = _history_to_contents(history)

    max_hops = 5
    for _ in range(max_hops):
        # 1) Ask the model
        try:
            resp = model.generate_content(
                contents=contents,
                generation_config={"temperature": 0.2},
            )
        except GoogleAPIError as e:
            reply = f"Upstream error from Gemini: {e}"
            history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "history": history}

        # 2) If no tool calls, we have a final answer
        calls = _extract_function_calls(resp)
        if not calls:
            final = _final_text(resp).strip()
            if not final:
                final = "Sorry, I couldn't produce a response."
            contents.append({"role": "model", "parts": [{"text": final}]})
            history.append({"role": "assistant", "content": final})
            return {"reply": final, "history": history}

        # 3) Append the MODEL function-call turn (mirrors exactly what the model requested)
        model_call_parts = []
        for c in calls:
            model_call_parts.append({
                "function_call": {
                    "name": c["name"],
                    "args": c["args"],
                }
            })
        contents.append({"role": "model", "parts": model_call_parts})

        # 4) Execute each tool and append TOOL responses (same count, same order)
        tool_parts = []
        for c in calls:
            name = c["name"]
            args = c["args"] if isinstance(c["args"], dict) else {}
            func = TOOL_FUNCS.get(name)
            if not func:
                tool_result = f"error: unknown tool {name}"
            else:
                try:
                    tool_result = func(**args)
                except TypeError as e:
                    tool_result = f"error: bad args for {name}: {e}"
                except Exception as e:
                    tool_result = f"error: {e}"

            payload = tool_result
            if isinstance(payload, str):
                payload = {"text": payload}

            tool_parts.append({
                "function_response": {
                    "name": name,
                    "response": payload
                }
            })

        contents.append({"role": "tool", "parts": tool_parts})
        # Outer loop repeats: we go back to (1) so the model can use tool outputs and produce final text

    # Safety break
    final = "Sorry, I couldn't complete that with the available tools."
    history.append({"role": "assistant", "content": final})
    return {"reply": final, "history": history}
