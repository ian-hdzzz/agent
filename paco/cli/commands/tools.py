"""paco tools -- MCP tool and server management."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli import api_client

app = typer.Typer(name="tools", help="MCP tool and server registry.")
console = Console()

STATUS_COLORS = {
    "online": "green",
    "offline": "red",
    "error": "red",
    "unknown": "yellow",
}


def _status_text(s: str) -> str:
    color = STATUS_COLORS.get(s, "white")
    return f"[{color}]{s}[/{color}]"


@app.command("list")
def list_tools(
    server_id: Optional[str] = typer.Option(None, "--server", help="Filter by MCP server ID"),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all registered tools."""
    try:
        tools = api_client.list_tools(server_id=server_id)
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    if as_json:
        console.print(json.dumps(tools, indent=2, default=str))
        return

    if not tools:
        console.print("[dim]No tools found.[/dim]")
        return

    table = Table(title="Tools")
    table.add_column("Name", style="bold")
    table.add_column("MCP Server")
    table.add_column("Enabled")
    table.add_column("Description", max_width=40)

    for t in tools:
        enabled = "[green]yes[/green]" if t.get("is_enabled") else "[red]no[/red]"
        desc = (t.get("description") or "-")[:40]
        table.add_row(
            t["name"],
            t.get("mcp_server_name") or "-",
            enabled,
            desc,
        )

    console.print(table)


@app.command("servers")
def list_servers(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List MCP servers."""
    try:
        servers = api_client.list_mcp_servers()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    if as_json:
        console.print(json.dumps(servers, indent=2, default=str))
        return

    if not servers:
        console.print("[dim]No MCP servers registered.[/dim]")
        return

    table = Table(title="MCP Servers")
    table.add_column("Name", style="bold")
    table.add_column("Transport")
    table.add_column("Status")
    table.add_column("URL", max_width=40)
    table.add_column("ID", style="dim")

    for s in servers:
        table.add_row(
            s["name"],
            s.get("transport", "?"),
            _status_text(s.get("status", "unknown")),
            s.get("url") or "-",
            s["id"][:8],
        )

    console.print(table)


@app.command()
def sync(server_id: str = typer.Argument(..., help="MCP server ID to sync tools from")):
    """Sync tools from an MCP server."""
    try:
        tools = api_client.sync_tools(server_id)
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(f"[green]Synced {len(tools)} tools.[/green]")
    for t in tools:
        console.print(f"  - {t['name']}")
