from pathlib import Path
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def test_streamlit_app_loads_and_runs():
    """Verify Streamlit app initializes, renders controls, and executes without errors."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    # No unhandled exceptions
    assert not at.exception

    # Check sidebar controls exist
    assert len(at.sidebar.selectbox) >= 3
    assert len(at.sidebar.button) >= 1

    # Verify initial events are present in session_state
    assert "events" in at.session_state
    assert len(at.session_state["events"]) > 0


def test_streamlit_app_click_run():
    """Verify clicking the 'Run Scenario' button updates events without error."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)

    at.run()

    # Trigger click on Run Scenario button
    at.sidebar.button[0].click().run()
    assert not at.exception

    events = at.session_state.get("events", [])
    assert len(events) >= 10
    # Confirm alert was recorded for attack scenario
    assert any(ev.get("type") == "alert" for ev in events)
