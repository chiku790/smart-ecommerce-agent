from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from app.agent import generate_memories_callback, memory_service, root_agent


def test_memory_bank_agent_configuration():
    assert memory_service is not None
    assert root_agent.after_agent_callback == generate_memories_callback
    tool_types = [type(t) for t in root_agent.tools]
    assert PreloadMemoryTool in tool_types
