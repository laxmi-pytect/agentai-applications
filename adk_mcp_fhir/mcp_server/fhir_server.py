"""
FHIR MCP Server
Exposes FHIR API operations as MCP tools that ADK can call.
"""

import os
import base64
import sys
import json
import asyncio
import urllib.request
import urllib.parse
import urllib.error
import time
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Initialize MCP server
app = Server("fhir-mcp-server")

# Load configuration from environment variables
FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL")
FHIR_USERNAME = os.environ.get("FHIR_USERNAME")
FHIR_PASSWORD = os.environ.get("FHIR_PASSWORD")
FHIR_AUTH_URL= os.environ.get("FHIR_AUTH_URL")




# ─────────────────────────────────────────────
# Tool Definitions
# ─────────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_patient_by_id",
            description="Get a FHIR Patient resource by its exact ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The FHIR ID of the patient"}
                },
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="search_patients_by_name",
            description="Search for FHIR Patients by their given or family name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to search for (e.g., 'Smith')"}
                },
                "required": ["name"]
            }
        ),
        types.Tool(
            name="get_patient_observations",
            description="Get Observations for a specific FHIR Patient by their ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The FHIR ID of the patient"}
                },
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="get_patient_encounters",
            description="Get Encounters for a specific FHIR Patient by their ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The FHIR ID of the patient"}
                },
                "required": ["patient_id"]
            }
        ),
        types.Tool(
            name="get_patient_procedures",
            description="Get Procedures for a specific FHIR Patient by their ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The FHIR ID of the patient"}
                },
                "required": ["patient_id"]
            }
        )
    ]


# ─────────────────────────────────────────────
# Tool Dispatcher & Implementations
# ─────────────────────────────────────────────

# Cache for the OAuth access token
_ACCESS_TOKEN = None
_TOKEN_EXPIRY = 0

async def fetch_fhir_data(url: str) -> str:
    """Helper method to run standard HTTP GET requests off the main thread."""
    def _fetch():
        global _ACCESS_TOKEN, _TOKEN_EXPIRY
        
        # Fetch a new token if we don't have one or if the current one is expired
        if not _ACCESS_TOKEN or time.time() >= _TOKEN_EXPIRY:
            auth_url=FHIR_AUTH_URL

            # Add Basic Authentication if credentials are provided
            b64_auth = ""
            if FHIR_USERNAME and FHIR_PASSWORD:
                auth_str = f"{FHIR_USERNAME}:{FHIR_PASSWORD}"
                b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('ascii')

            payload = "grant_type=client_credentials&scope=system%2FPatient.read%2C%20system%2FCondition.read%2C%20system%2FEncounter.read%2C%20system%2FDiagnosticReport.read%2C%20system%2FDocumentReference.read%2C%20system%2FBinary.read%2C%20system%2FObservation.read%2C%20system%2FProcedure.read"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            }
            if b64_auth:
                headers["Authorization"] = f"Basic {b64_auth}"

            auth_response = requests.request("POST", auth_url, headers=headers, data=payload)

            try:
                auth_data = auth_response.json()
                _ACCESS_TOKEN = auth_data["access_token"]
                expires_in = auth_data.get("expires_in", 300)
                _TOKEN_EXPIRY = time.time() + expires_in - 10 # Buffer of 10s
            except Exception as e:
                # Write to stderr so we don't corrupt the MCP stdout JSON stream
                print(f"[ERROR] Auth response: {auth_response.text}", file=sys.stderr)
                raise Exception(f"Failed to get access token. Status: {auth_response.status_code}, Response: {auth_response.text}")
        
        req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization": f"Bearer {_ACCESS_TOKEN}"})
        
        try:
            with urllib.request.urlopen(req) as response:
                return response.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            # Read the actual error body returned by the FHIR server (e.g., OperationOutcome)
            error_body = e.read().decode('utf-8')
            print(f"\n[SERVER ERROR] HTTP {e.code} for URL {url}\nResponse: {error_body}\n", file=sys.stderr)
            raise Exception(f"HTTP {e.code}: {error_body}")
        except Exception as e:
            print(f"\n[SERVER ERROR] Unknown fetch error: {str(e)}\n", file=sys.stderr)
            raise

    return await asyncio.to_thread(_fetch)


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "get_patient_by_id":
            patient_id = arguments["patient_id"]
            url = f"{FHIR_BASE_URL}/Patient?_id={patient_id}"
            data = await fetch_fhir_data(url)
            return [types.TextContent(type="text", text=data)]
            
        elif name == "search_patients_by_name":
            name_query = urllib.parse.quote(arguments["name"])
            url = f"{FHIR_BASE_URL}/Patient?name={name_query}"
            data = await fetch_fhir_data(url)
            return [types.TextContent(type="text", text=data)]
            
        elif name == "get_patient_observations":
            patient_id = arguments["patient_id"]
            url = f"{FHIR_BASE_URL}/Observation?patient={patient_id}"
            data = await fetch_fhir_data(url)
            return [types.TextContent(type="text", text=data)]
            
        elif name == "get_patient_encounters":
            patient_id = arguments["patient_id"]
            url = f"{FHIR_BASE_URL}/Encounter?patient={patient_id}"
            data = await fetch_fhir_data(url)
            return [types.TextContent(type="text", text=data)]
            
        elif name == "get_patient_procedures":
            patient_id = arguments["patient_id"]
            url = f"{FHIR_BASE_URL}/Procedure?patient={patient_id}"
            data = await fetch_fhir_data(url)
            return [types.TextContent(type="text", text=data)]
            
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        print(f"\n[SERVER ERROR] Tool execution failed: {str(e)}\n", file=sys.stderr)
        return [types.TextContent(type="text", text=f"FHIR API Error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())