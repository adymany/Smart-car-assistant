from .car_state import CarState


def set_ac(state: CarState, on: str = "on", **kwargs) -> str:
    state.ac_on = (on.lower() == "on")
    
    # Handle both 'temperature' and 'temp' shorthands from different models
    temperature = kwargs.get("temperature") or kwargs.get("temp")
    
    if temperature is not None:
        state.ac_temp = max(16, min(30, int(temperature)))
    return f"AC {'turned on' if state.ac_on else 'turned off'}" + (f" at {state.ac_temp}°C" if state.ac_on else "")

def navigate_to(state: CarState, destination: str) -> str:
    state.destination = destination
    return f"Navigating to {destination}. ETA 28 minutes."

def stop_navigation(state: CarState) -> str:
    state.destination = None
    return "Navigation cancelled."

def toggle_lights(state: CarState, on: str) -> str:
    state.lights_on = (on.lower() == "on")
    return f"Headlights {'on' if state.lights_on else 'off'}."

def toggle_wipers(state: CarState, on: str) -> str:
    state.wipers_on = (on.lower() == "on")
    return f"Wipers {'activated' if state.wipers_on else 'stopped'}."

def control_window(state: CarState, window: str, action: str) -> str:
    target_state = 100 if action.lower() == "open" else 0
    
    if window in ["driver", "all"]:
        state.windows["driver"] = target_state
    if window in ["passenger", "all"]:
        state.windows["passenger"] = target_state
        
    return f"{window.capitalize()} window(s) {action}ed."
