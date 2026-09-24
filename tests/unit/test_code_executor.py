from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from app.agent import root_agent, code_executor


def test_agent_code_executor_configuration():
    assert root_agent.code_executor is not None
    assert isinstance(root_agent.code_executor, AgentEngineSandboxCodeExecutor)
    assert code_executor.agent_engine_resource_name == "projects/40148140586/locations/us-east1/reasoningEngines/7515797493569814528"
