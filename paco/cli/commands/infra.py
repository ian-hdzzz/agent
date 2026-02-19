"""paco infra -- infrastructure management."""

import json

import typer
from rich.console import Console
from rich.table import Table

from cli import api_client

app = typer.Typer(name="infra", help="Multi-agent infrastructure management.")
console = Console()

STATUS_COLORS = {
    "active": "green",
    "running": "green",
    "draft": "yellow",
    "stopped": "yellow",
    "error": "red",
}


def _status_text(s: str) -> str:
    color = STATUS_COLORS.get(s, "white")
    return f"[{color}]{s}[/{color}]"


@app.command("list")
def list_infra(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all infrastructures."""
    try:
        infras = api_client.list_infrastructures()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    if as_json:
        console.print(json.dumps(infras, indent=2, default=str))
        return

    if not infras:
        console.print("[dim]No infrastructures found.[/dim]")
        return

    table = Table(title="Infrastructures")
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Agents", justify="right")
    table.add_column("Orchestrator")
    table.add_column("Version")

    for i in infras:
        has_orch = "[green]yes[/green]" if i.get("has_orchestrator") else "[dim]no[/dim]"
        table.add_row(
            i.get("display_name") or i["name"],
            i.get("type", "orchestrator"),
            _status_text(i.get("status", "?")),
            str(i.get("agent_count", 0)),
            has_orch,
            i.get("version", "-"),
        )

    console.print(table)


@app.command()
def show(infra_id: str = typer.Argument(..., help="Infrastructure ID")):
    """Show detailed infrastructure info with orchestrator and agents."""
    try:
        detail = api_client.get_infrastructure(infra_id)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(json.dumps(detail, indent=2, default=str))
