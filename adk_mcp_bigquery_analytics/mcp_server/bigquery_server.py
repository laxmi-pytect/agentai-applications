"""
BigQuery MCP Server
Exposes BigQuery operations as MCP tools that ADK can call.
"""

import json
import asyncio
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

# Initialize MCP server
app = Server("bigquery-mcp-server")

# BigQuery client (uses Application Default Credentials)
bq_client = bigquery.Client()


# ─────────────────────────────────────────────
# Tool: list_datasets
# ─────────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_datasets",
            description="List all datasets in the BigQuery project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "GCP project ID. Defaults to the client project."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="list_tables",
            description="List all tables in a BigQuery dataset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "The BigQuery dataset ID."
                    },
                    "project_id": {
                        "type": "string",
                        "description": "GCP project ID. Defaults to the client project."
                    }
                },
                "required": ["dataset_id"]
            }
        ),
        types.Tool(
            name="get_table_schema",
            description="Get the schema of a BigQuery table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string"},
                    "table_id": {"type": "string"},
                    "project_id": {"type": "string"}
                },
                "required": ["dataset_id", "table_id"]
            }
        ),
        types.Tool(
            name="run_query",
            description="Run a SQL query on BigQuery and return results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Standard SQL query to execute."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of rows to return. Default: 100.",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_table_preview",
            description="Preview the first N rows of a BigQuery table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string"},
                    "table_id": {"type": "string"},
                    "project_id": {"type": "string"},
                    "max_rows": {
                        "type": "integer",
                        "description": "Number of rows to preview. Default: 10.",
                        "default": 10
                    }
                },
                "required": ["dataset_id", "table_id"]
            }
        ),
        types.Tool(
            name="create_dataset",
            description="Create a new BigQuery dataset.",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string"},
                    "location": {
                        "type": "string",
                        "description": "Dataset location, e.g. 'US', 'EU'. Default: 'US'.",
                        "default": "US"
                    },
                    "description": {"type": "string"}
                },
                "required": ["dataset_id"]
            }
        ),
    ]


# ─────────────────────────────────────────────
# Tool Dispatcher
# ─────────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        if name == "list_datasets":
            return await _list_datasets(arguments)
        elif name == "list_tables":
            return await _list_tables(arguments)
        elif name == "get_table_schema":
            return await _get_table_schema(arguments)
        elif name == "run_query":
            return await _run_query(arguments)
        elif name == "get_table_preview":
            return await _get_table_preview(arguments)
        elif name == "create_dataset":
            return await _create_dataset(arguments)
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    except GoogleAPIError as e:
        return [types.TextContent(type="text", text=f"BigQuery API error: {str(e)}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────
async def _list_datasets(args: dict) -> list[types.TextContent]:
    project = args.get("project_id", bq_client.project)
    datasets = list(bq_client.list_datasets(project=project))
    if not datasets:
        return [types.TextContent(type="text", text="No datasets found.")]
    result = [f"Datasets in project '{project}':"]
    for ds in datasets:
        result.append(f"  - {ds.dataset_id}")
    return [types.TextContent(type="text", text="\n".join(result))]


async def _list_tables(args: dict) -> list[types.TextContent]:
    project = args.get("project_id", bq_client.project)
    dataset_id = args["dataset_id"]
    tables = list(bq_client.list_tables(f"{project}.{dataset_id}"))
    if not tables:
        return [types.TextContent(type="text", text=f"No tables found in dataset '{dataset_id}'.")]
    result = [f"Tables in '{project}.{dataset_id}':"]
    for t in tables:
        result.append(f"  - {t.table_id} ({t.table_type})")
    return [types.TextContent(type="text", text="\n".join(result))]


async def _get_table_schema(args: dict) -> list[types.TextContent]:
    project = args.get("project_id", bq_client.project)
    table_ref = f"{project}.{args['dataset_id']}.{args['table_id']}"
    table = bq_client.get_table(table_ref)
    schema_info = [f"Schema for `{table_ref}`:"]
    for field in table.schema:
        nullable = "NULLABLE" if field.mode == "NULLABLE" else field.mode
        schema_info.append(f"  {field.name}: {field.field_type} ({nullable})"
                           + (f" — {field.description}" if field.description else ""))
    schema_info.append(f"\nRow count: {table.num_rows:,}")
    schema_info.append(f"Size: {table.num_bytes / 1e6:.2f} MB")
    return [types.TextContent(type="text", text="\n".join(schema_info))]


async def _run_query(args: dict) -> list[types.TextContent]:
    query = args["query"]
    max_results = args.get("max_results", 100)
    job = bq_client.query(query)
    rows = list(job.result(max_results=max_results))
    if not rows:
        return [types.TextContent(type="text", text="Query returned no results.")]
    # Build table output
    headers = [field.name for field in rows[0]._fields]
    lines = [" | ".join(headers)]
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(v) for v in row.values()))
    lines.append(f"\n({len(rows)} rows returned)")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _get_table_preview(args: dict) -> list[types.TextContent]:
    project = args.get("project_id", bq_client.project)
    max_rows = args.get("max_rows", 10)
    table_ref = f"{project}.{args['dataset_id']}.{args['table_id']}"
    query = f"SELECT * FROM `{table_ref}` LIMIT {max_rows}"
    return await _run_query({"query": query, "max_results": max_rows})


async def _create_dataset(args: dict) -> list[types.TextContent]:
    dataset_id = args["dataset_id"]
    location = args.get("location", "US")
    description = args.get("description", "")
    dataset = bigquery.Dataset(f"{bq_client.project}.{dataset_id}")
    dataset.location = location
    dataset.description = description
    created = bq_client.create_dataset(dataset, exists_ok=True)
    return [types.TextContent(
        type="text",
        text=f"Dataset '{created.dataset_id}' created in location '{created.location}'."
    )]


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
    