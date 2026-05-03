import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

# Import the agent and toolset we configured
from agent import root_agent, mcp_toolset

async def main():
    print("🔗 Connecting to FHIR MCP Server...")
    print("✅ FHIR Agent ready! Type your queries (or 'quit' to exit).\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue

            # Setup an ADK session for this turn
            session_service = InMemorySessionService()
            session = await session_service.create_session(
                app_name="fhir-agent",
                user_id="user_1",
            )

            runner = Runner(
                agent=root_agent,
                app_name="fhir-agent",
                session_service=session_service,
            )

            # Stream the interaction with the ADK agent
            response_parts = []
            async for event in runner.run_async(
                user_id="user_1",
                session_id=session.id,
                new_message=Content(role="user", parts=[Part(text=user_input)])
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # 1. Log the background tool activity to the console
                        if part.function_call:
                            print(f"\n[🔧 Tool Call] Agent is fetching data using: {part.function_call.name} (args: {part.function_call.args})")
                        elif part.function_response:
                            print(f"[✅ Tool Response] Received data from: {part.function_response.name}")
                            # Print a snippet of the raw payload so you can see any embedded errors
                            print(f"   ↳ Raw Output: {str(part.function_response.response)[:300]}...\n")
                            
                        # 2. Extract text safely to avoid the "non-text parts" warning
                        if event.is_final_response() and not part.function_call and not part.function_response:
                            if getattr(part, "text", None):
                                response_parts.append(part.text)

            print(f"\nAgent: {''.join(response_parts)}\n")

    finally:
        # Gracefully shut down the MCP stdio connection
        await mcp_toolset.close()
        print("👋 Connection closed.")

if __name__ == "__main__":
    asyncio.run(main())