import os
from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import pathlib

import os
from dotenv import load_dotenv
load_dotenv()




# Absolute path to the MCP server so ADK Web can find it
MCP_SERVER_PATH = str(
    pathlib.Path(__file__).parent.parent / "mcp_server" / "bigquery_server.py"
)

mcp_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH],
        env={
            "GOOGLE_APPLICATION_CREDENTIALS": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
            "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        }
    )
)

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="bigquery_adk_agent",
    description="A BigQuery assistant that can query and manage BigQuery resources.",
    instruction="""
        You are a BigQuery data assistant. You can help users:
        - List datasets and tables in their GCP project
        - Inspect table schemas and previews
        - Run SQL queries on BigQuery
        - Create new datasets

        Always confirm destructive operations before executing them.
        Format query results clearly in markdown tables when possible.
    """,
    tools=[mcp_toolset],
)