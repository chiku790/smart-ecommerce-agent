from app.a2ui_utils import a2ui_callback
from app.agent import root_agent


def test_a2ui_agent_configuration():
    assert root_agent.after_model_callback == a2ui_callback
    assert "beginRendering" in root_agent.instruction or "A2UI" in root_agent.instruction
