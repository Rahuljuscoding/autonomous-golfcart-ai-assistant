"""
This script is a determistic finite state machine that interprets the live cart metadata and 
assigns a semantic state. 

"""

STOPPED_AT_STOP = "STOPPED_AT_STOP"
MOVING_BETWEEN_STOPS = "MOVING_BETWEEN_STOPS"
APPROACHING_STOP = "APPROACHING_STOP"

#distance threshold to consider "approaching"
APPROACHING_DISTANCE_M = 20.0

def classify_cart_state(cart_state: dict) -> dict:

    is_stopped = cart_state["is_stopped"]
    distance_to_next = cart_state["distance_to_next_stop_m"]

    current_stop = cart_state["current_stop"]
    next_stop = cart_state["next_stop"]

    # Cart is stopped at a stop
    if is_stopped:
        return {
            "state": STOPPED_AT_STOP,
            "current_stop": current_stop,
            "next_stop": next_stop,
            "last_stop": current_stop
        }

    # Cart is moving and close to next stop
    if distance_to_next <= APPROACHING_DISTANCE_M:
        return {
            "state": APPROACHING_STOP,
            "current_stop": current_stop,
            "next_stop": next_stop,
            "last_stop": current_stop
        }

    # Cart is moving normally between stops
    return {
        "state": MOVING_BETWEEN_STOPS,
        "current_stop": current_stop,
        "next_stop": next_stop,
        "last_stop": current_stop
    }

