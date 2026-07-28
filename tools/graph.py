class GraphAPITool:
    """Tool for reading user's mail, teams chats via Graph API."""
    def __init__(self):
        self.name = "graph_api_integration"
        self.description = "Integrates with Microsoft Graph API for emails and chats."

    def execute(self, query: str) -> str:
        # Stub for Graph API
        return f"Fetched data from Graph API for query: {query}"
