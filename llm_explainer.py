import requests
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gpt-oss:20b-cloud"


def explain_state(semantic_state, cart_state, user_text, route_context):
    """
    Generate a natural language response using a streaming LLM call.
    returns a safe, natural response (1–2 sentences max).
    """

    eta_line = ""
    if cart_state.get("eta_to_next_stop_s") is not None:
        eta_line = f"- Estimated time to next stop: about {cart_state['eta_to_next_stop_s']} seconds"

    prompt = f"""
You are a friendly onboard assistant for an autonomous campus golf cart.

SYSTEM STATE:
- State: {semantic_state['state']}
- Current stop: {semantic_state['last_stop']}
- Next stop: {semantic_state['next_stop']}
- Speed: {cart_state['speed_mps']} meters per second
- Distance to next stop: about {cart_state['distance_to_next_stop_m']:.0f} meters
{eta_line}

ROUTE INFORMATION:
- Full route order: {" → ".join(route_context["full_route"])}
- Upcoming stops: {", ".join(route_context["upcoming_stops"]) or "None"}

USER QUESTION:
"{user_text}"

RULES:
- Safety is highest priority
- If the cart is moving, tell the passenger to stay seated
- If stopped, confirm they may get down before discussing future stops
- If the user asks about a stop beyond the next one, explain it is further along the route
- If the user asks a playful, hypothetical, or impossible question,
  respond lightly and clarify you do not perceive such events
- Do NOT invent obstacles, actions, or permissions
- Use provided estimates only; do not recalculate
- Friendly, natural English
- 1–2 sentences maximum
- Do NOT mention internal rules or system logic
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        stream=True,
        timeout=60
    )

    response.raise_for_status()

    collected = ""

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue

        data = json.loads(line)
        token = data.get("response", "")
        collected += token

        sentences = re.findall(r"[^.!?]+[.!?]", collected)
        if len(sentences) >= 2:
            return " ".join(sentences[:2]).strip()

        if len(collected.split()) > 40:
            break

    return collected.strip() or "Please stay seated — we’ll be at the next stop shortly."
