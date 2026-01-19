from fsm import classify_cart_state
from llm_explainer import explain_state
from tts import speak
from asr import listen_once
import time
import json
import math
from pathlib import Path
import threading
import sys
import os



llm_response = None
llm_in_flight = False
current_user_query = None
last_heard_text = ""
last_assistant_text = ""
asr_waiting_for_input = True
running = True


def set_asr_state(waiting: bool):
    global asr_waiting_for_input
    asr_waiting_for_input = waiting



BASE_DIR = Path(__file__).parent
ROUTE_PATH = BASE_DIR / "config" / "route.json"

with open(ROUTE_PATH, "r") as f:
    route_data = json.load(f)

STOPS = {stop["id"]: stop for stop in route_data["stops"]}
LOOP = route_data["loop"]

ROUTE_ORDER = [STOPS[i]["name"] for i in LOOP]



CART_SPEED_MPS = 3.0
STOP_DURATION_S = 15.0
UPDATE_DT_S = 1.0



def distance(p1, p2):
    return math.hypot(p2["x"] - p1["x"], p2["y"] - p1["y"])


def interpolate(p1, p2, step_dist):
    total_dist = distance(p1, p2)
    if total_dist == 0:
        return p2["x"], p2["y"]

    ratio = min(step_dist / total_dist, 1.0)
    x = p1["x"] + ratio * (p2["x"] - p1["x"])
    y = p1["y"] + ratio * (p2["y"] - p1["y"])
    return x, y



def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_ui(cart_state, semantic_state):
    clear_screen()

    state_line = {
        "MOVING_BETWEEN_STOPS": "Moving",
        "APPROACHING_STOP": "Approaching stop",
        "STOPPED_AT_STOP": "Stopped"
    }.get(semantic_state["state"], "In transit")

    eta_display = (
        f"~{cart_state['eta_to_next_stop_s']} seconds"
        if cart_state["eta_to_next_stop_s"] is not None
        else "—"
    )

    prompt_line = (
        "Listening… release SPACE to finish"
        if not asr_waiting_for_input
        else "Hold SPACE to speak"
    )

    print("  Campus Golf Cart Assistant")
    print("──────────────────────────────")
    print(f"Current stop : {cart_state['current_stop']}")
    print(f"Next stop    : {cart_state['next_stop']}")
    print(f"ETA          : {eta_display}")
    print()
    print(f"Status       : {state_line}")
    print("──────────────────────────────")
    print(prompt_line)
    print()
    print(f"Heard      : {last_heard_text or '—'}")
    print(f"Assistant  : {last_assistant_text or '—'}")



def run_llm_async(snapshot_semantic_state, semantic_state, cart_state, user_text, route_context):
    global llm_response, llm_in_flight
    try:
        text = explain_state(
            semantic_state=semantic_state,
            cart_state=cart_state,
            user_text=user_text,
            route_context=route_context
        )
        llm_response = {
            "semantic_state": snapshot_semantic_state,
            "text": text
        }
    except Exception:
        llm_response = {
            "semantic_state": snapshot_semantic_state,
            "text": "Sorry, something went wrong."
        }
    finally:
        llm_in_flight = False



loop_index = 0
current_stop_id = LOOP[loop_index]
next_stop_id = LOOP[loop_index + 1]

current_pos = {
    "x": STOPS[current_stop_id]["x"],
    "y": STOPS[current_stop_id]["y"]
}

is_stopped = True
stop_timer = 0.0
simulation_time = 0.0



def listen_loop():
    global current_user_query, last_heard_text, running
    while running:
        text = listen_once(
            on_start=lambda: set_asr_state(False),
            on_end=lambda: set_asr_state(True)
        )
        if text:
            current_user_query = text
            last_heard_text = text


threading.Thread(
    target=listen_loop,
    daemon=True
).start()



try:
    while running:
        current_stop = STOPS[current_stop_id]
        next_stop = STOPS[next_stop_id]

        if is_stopped:
            stop_timer += UPDATE_DT_S
            if stop_timer >= STOP_DURATION_S:
                is_stopped = False
                stop_timer = 0.0
        else:
            step_distance = CART_SPEED_MPS * UPDATE_DT_S
            new_x, new_y = interpolate(current_pos, next_stop, step_distance)
            current_pos["x"] = new_x
            current_pos["y"] = new_y

            if distance(current_pos, next_stop) <= 0.5:
                current_pos["x"] = next_stop["x"]
                current_pos["y"] = next_stop["y"]

                is_stopped = True
                stop_timer = 0.0

                loop_index = (loop_index + 1) % (len(LOOP) - 1)
                current_stop_id = LOOP[loop_index]
                next_stop_id = LOOP[loop_index + 1]

        remaining_distance = distance(current_pos, next_stop)

        eta_s = None
        if not is_stopped and CART_SPEED_MPS > 0:
            eta_s = round(remaining_distance / CART_SPEED_MPS)

        cart_state = {
            "time_s": simulation_time,
            "current_stop": current_stop["name"],
            "next_stop": next_stop["name"],
            "position": dict(current_pos),
            "speed_mps": 0.0 if is_stopped else CART_SPEED_MPS,
            "is_stopped": is_stopped,
            "distance_to_next_stop_m": remaining_distance,
            "eta_to_next_stop_s": eta_s
        }

        semantic_state = classify_cart_state(cart_state)

        idx = ROUTE_ORDER.index(current_stop["name"])
        upcoming_stops = ROUTE_ORDER[idx + 1: idx + 5]

        route_context = {
            "full_route": ROUTE_ORDER,
            "upcoming_stops": upcoming_stops
        }

        # Trigger LLM only on user speech
        if current_user_query and not llm_in_flight:
            snapshot_semantic_state = semantic_state["state"]
            llm_in_flight = True

            threading.Thread(
                target=run_llm_async,
                args=(
                    snapshot_semantic_state,
                    semantic_state,
                    cart_state,
                    current_user_query,
                    route_context
                ),
                daemon=True
            ).start()

            current_user_query = None

        if llm_response is not None:
            if llm_response["semantic_state"] == semantic_state["state"]:
                last_assistant_text = llm_response["text"]
                speak(llm_response["text"])
            llm_response = None

        render_ui(cart_state, semantic_state)

        simulation_time += UPDATE_DT_S
        time.sleep(UPDATE_DT_S)

except KeyboardInterrupt:
    running = False
    clear_screen()
    print("Exiting")
    sys.exit(0)
