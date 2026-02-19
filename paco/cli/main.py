"""
PACO CLI -- power-user tool for agent deployment, tool sync, and infra management.

Usage:
    paco auth login
    paco agents list
    paco agents start <name>
    paco skills list
    paco tools list
    paco infra list
    paco status
"""

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.commands import agents, auth, infra, skills, tools

app = typer.Typer(
    name="paco",
    help="PACO CLI -- manage agents, skills, tools, and infrastructure.",
    no_args_is_help=True,
)

app.add_typer(auth.app, name="auth")
app.add_typer(agents.app, name="agents")
app.add_typer(skills.app, name="skills")
app.add_typer(tools.app, name="tools")
app.add_typer(infra.app, name="infra")

console = Console()


@app.command()
def status():
    """Overview dashboard: agents, skills, tools summary."""
    from cli import api_client, config

    creds = config.load_credentials()
    if not creds:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]User:[/bold] {creds.get('name', '?')} ({creds.get('email', '?')})\n"
        f"[bold]Role:[/bold] {creds.get('role', '?')}\n"
        f"[bold]API:[/bold] {config.get_api_url()}",
        title="PACO Status",
    ))

    # Agents summary
    try:
        agents_list = api_client.list_agents()
        total = len(agents_list)
        running = sum(1 for a in agents_list if a.get("status") == "running")
        stopped = sum(1 for a in agents_list if a.get("status") == "stopped")
        errors = sum(1 for a in agents_list if a.get("status") in ("error", "errored"))

        table = Table(title="Agents", show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_row("Total", str(total))
        table.add_row("Running", f"[green]{running}[/green]")
        table.add_row("Stopped", f"[yellow]{stopped}[/yellow]")
        table.add_row("Errors", f"[red]{errors}[/red]")
        console.print(table)
    except Exception:
        console.print("[dim]Could not fetch agents.[/dim]")

    # Skills summary
    try:
        skills_list = api_client.list_skills()
        active = sum(1 for s in skills_list if s.get("is_active"))
        console.print(f"\n[bold]Skills:[/bold] {len(skills_list)} total, [green]{active} active[/green]")
    except Exception:
        console.print("[dim]Could not fetch skills.[/dim]")

    # Tools summary
    try:
        tools_list = api_client.list_tools()
        enabled = sum(1 for t in tools_list if t.get("is_enabled"))
        console.print(f"[bold]Tools:[/bold] {len(tools_list)} total, [green]{enabled} enabled[/green]")
    except Exception:
        console.print("[dim]Could not fetch tools.[/dim]")

    # Infra summary
    try:
        infra_list = api_client.list_infrastructures()
        console.print(f"[bold]Infrastructures:[/bold] {len(infra_list)}")
    except Exception:
        console.print("[dim]Could not fetch infrastructures.[/dim]")


@app.command("config")
def show_config(
    api_url: str = typer.Option(None, "--api-url", help="Set the API base URL"),
):
    """View or update CLI configuration."""
    from cli import config as cfg

    if api_url:
        cfg.set_api_url(api_url)
        console.print(f"[green]API URL set to:[/green] {api_url}")
        return

    console.print(f"[bold]API URL:[/bold] {cfg.get_api_url()}")
    console.print(f"[bold]Config dir:[/bold] {cfg.PACO_DIR}")
    console.print(f"[bold]Credentials:[/bold] {'exists' if cfg.CREDENTIALS_FILE.exists() else 'not found'}")


if __name__ == "__main__":
    app()
