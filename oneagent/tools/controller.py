import subprocess
import shlex

class ComputerControllerTool:
    """Tool for controlling user's computer (OpenManus/OS control simulation)."""
    def __init__(self):
        self.name = "computer_controller"
        self.description = "Controls the local computer to execute tasks."
        # Highly restricted list of allowed safe commands
        self.allowed_commands = ["ls", "pwd", "whoami", "date", "echo"]

    def execute(self, action: str) -> str:
        # A basic implementation that runs shell commands (safe restricted)
        try:
            # Parse the command to check if it's safe
            args = shlex.split(action)
            if not args:
                return "Empty command"

            base_cmd = args[0]
            if base_cmd not in self.allowed_commands:
                return f"Command '{base_cmd}' is not allowed for security reasons. Allowed commands: {', '.join(self.allowed_commands)}"

            # Safely execute without shell=True
            result = subprocess.run(args, capture_output=True, text=True, timeout=10)
            output = result.stdout if result.stdout else result.stderr
            return f"Executed '{action}'. Output: {output[:500]}"
        except Exception as e:
            return f"Failed to execute '{action}': {str(e)}"
