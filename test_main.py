from agent.core import SuperAgent
from providers.llm import OpenAICompatibleProvider
from memory.storage import MemorySystem
from tools.controller import ComputerControllerTool

def test():
    memory = MemorySystem()
    provider = OpenAICompatibleProvider(model="stub")
    agent = SuperAgent(provider=provider, memory_system=memory)
    agent.add_tool(ComputerControllerTool())

    # Test safe command
    tool = agent.tools["computer_controller"]
    safe_out = tool.execute("echo 'hello'")
    assert "hello" in safe_out, f"Expected hello in {safe_out}"

    # Test unsafe command
    unsafe_out = tool.execute("rm -rf /")
    assert "not allowed for security reasons" in unsafe_out, f"Expected security rejection in {unsafe_out}"

    print("Security tests passed!")

    # Test tool loop stub
    response = agent.process_input("use_tool test")
    print("Response:", response)

if __name__ == "__main__":
    test()
