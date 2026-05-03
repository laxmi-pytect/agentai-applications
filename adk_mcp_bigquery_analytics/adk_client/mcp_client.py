"""
Google ADK Agent acting as an MCP Client.
Connects to the BigQuery MCP server via stdio and exposes
its tools to the ADK agent for natural language interactions.
"""

import asyncio
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

import os
from dotenv import load_dotenv
load_dotenv()


# ─────────────────────────────────────────────
# Build ADK Agent with MCP BigQuery tools
# ─────────────────────────────────────────────

async def create_bigquery_agent():

    mcp_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="python",
            args=["../mcp_server/bigquery_server.py"],
        )
    )

    agent = LlmAgent(
        model="gemini-2.5-flash",
        name="bigquery_agent",
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

    return agent, mcp_toolset


# ─────────────────────────────────────────────
# Interactive CLI loop
# ─────────────────────────────────────────────
async def main():
    print("🔗 Connecting to BigQuery MCP Server...")
    agent, mcp_toolset = await create_bigquery_agent()

    print("✅ BigQuery Agent ready! Type your queries (or 'quit' to exit).\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai.types import Content, Part

            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name="bigquery-agent",
                user_id="user_1",
            )

            runner = Runner(
                agent=agent,
                app_name="bigquery-agent",
                session_service=session_service,
            )

            response_parts = []
            async for event in runner.run_async(
                user_id="user_1",
                session_id=session.id,
                new_message=Content(role="user", parts=[Part(text=user_input)])
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if part.text:
                            response_parts.append(part.text)

            print(f"\nAgent: {''.join(response_parts)}\n")

    finally:
        await mcp_toolset.close()
        print("👋 Connection closed.")


if __name__ == "__main__":
    asyncio.run(main())
