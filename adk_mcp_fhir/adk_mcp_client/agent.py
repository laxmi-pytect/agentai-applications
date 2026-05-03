from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import pathlib

import os
from datetime import timedelta
import mcp.client.session

# --- FIX: Override Google ADK's Hardcoded 5-Second Timeout ---
# The Google ADK framework currently hardcodes a 5-second timeout for local MCP tools.
# We monkeypatch the underlying MCP ClientSession to bypass this and allow 30 seconds.
_orig_init = mcp.client.session.ClientSession.__init__

def _patched_init(self, *args, **kwargs):
    kwargs['read_timeout_seconds'] = timedelta(seconds=30.0)
    _orig_init(self, *args, **kwargs)

mcp.client.session.ClientSession.__init__ = _patched_init
from dotenv import load_dotenv
load_dotenv()


# Absolute path to the FHIR MCP server so ADK Web can find it
MCP_SERVER_PATH = str(
    pathlib.Path(__file__).parent.parent / "mcp_server" / "fhir_server.py"
)

mcp_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=[MCP_SERVER_PATH]
    )
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='fhir_agent',
    description='A helpful assistant that queries FHIR APIs.',
    instruction='''
        You are a clinical data assistant. You can help users:
        - Fetch a Patient's demographic details by their exact ID
        - Search for a list of Patients by their name
        - Fetch a Patient's Observations, Encounters, and Procedures by their exact ID
        
        Use the provided MCP tools to query the FHIR server. Always format patient information clearly for the user.
    ''',
    tools=[mcp_toolset]
)
