"""paco agents -- agent lifecycle management."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from cli import api_client

app = typer.Typer(name="agents", help="Agent management and lifecycle.")
console = Console()

STATUS_COLORS = {
    "running": "green",
    "online": "green",
    "stopped": "yellow",
    "error": "red",
    "errored": "red",
    "starting": "cyan",
    "stopping": "cyan",
}


def _status_text(s: str) -> str:
    color = STATUS_COLORS.get(s, "white")
    return f"[{color}]{s}[/{color}]"


def _resolve_agent_id(name: str) -> str:
    """Resolve an agent name to its UUID."""
    agents = api_client.list_agents()
    for a in agents:
        if a["name"] == name or a["id"] == name:
            return a["id"]
    console.print(f"[red]Agent '{name}' not found.[/red]")
    raise typer.Exit(1)


@app.command("list")
def list_agents(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all registered agents."""
    try:
        agents = api_client.list_agents()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    if as_json:
        console.print(json.dumps(agents, indent=2, default=str))
        return

    if not agents:
        console.print("[dim]No agents registered.[/dim]")
        return

    table = Table(title="Agents")
    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Port")
    table.add_column("ID", style="dim")

    for a in agents:
        table.add_row(
            a.get("display_name") or a["name"],
            _status_text(a["status"]),
            a.get("model", "-"),
            str(a.get("port") or "-"),
            a["id"][:8],
        )

    console.print(table)


@app.command()
def show(name: str = typer.Argument(..., help="Agent name or ID")):
    """Show detailed info for a single agent."""
    agent_id = _resolve_agent_id(name)
    try:
        detail = api_client.get_agent(agent_id)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(json.dumps(detail, indent=2, default=str))


@app.command()
def start(name: str = typer.Argument(..., help="Agent name or ID")):
    """Start an agent via PM2."""
    agent_id = _resolve_agent_id(name)
    try:
        result = api_client.start_agent(agent_id)
    except api_client.APIError as e:
        console.print(f"[red]Failed to start:[/red] {e.detail}")
        raise typer.Exit(1)

    agent = result.get("agent", {})
    console.print(
        f"[green]Started[/green] {agent.get('name', name)} "
        f"-- status: {_status_text(agent.get('status', '?'))}"
    )


@app.command()
def stop(name: str = typer.Argument(..., help="Agent name or ID")):
    """Stop an agent via PM2."""
    agent_id = _resolve_agent_id(name)
    try:
        result = api_client.stop_agent(agent_id)
    except api_client.APIError as e:
        console.print(f"[red]Failed to stop:[/red] {e.detail}")
        raise typer.Exit(1)

    agent = result.get("agent", {})
    console.print(
        f"[yellow]Stopped[/yellow] {agent.get('name', name)} "
        f"-- status: {_status_text(agent.get('status', '?'))}"
    )


@app.command()
def restart(name: str = typer.Argument(..., help="Agent name or ID")):
    """Restart an agent via PM2."""
    agent_id = _resolve_agent_id(name)
    try:
        result = api_client.restart_agent(agent_id)
    except api_client.APIError as e:
        console.print(f"[red]Failed to restart:[/red] {e.detail}")
        raise typer.Exit(1)

    agent = result.get("agent", {})
    console.print(
        f"[green]Restarted[/green] {agent.get('name', name)} "
        f"-- status: {_status_text(agent.get('status', '?'))}"
    )


@app.command("status")
def agent_status(name: str = typer.Argument(..., help="Agent name or ID")):
    """Get live PM2 status for an agent."""
    agent_id = _resolve_agent_id(name)
    try:
        result = api_client.get_agent_status(agent_id)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(json.dumps(result, indent=2, default=str))
