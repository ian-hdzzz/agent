"""paco skills -- skill browsing and sync."""

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli import api_client

app = typer.Typer(name="skills", help="Skill registry management.")
console = Console()


@app.command("list")
def list_skills(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all registered skills."""
    try:
        skills = api_client.list_skills()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    if as_json:
        console.print(json.dumps(skills, indent=2, default=str))
        return

    if not skills:
        console.print("[dim]No skills found.[/dim]")
        return

    table = Table(title="Skills")
    table.add_column("Code", style="bold")
    table.add_column("Name")
    table.add_column("Active")
    table.add_column("Agents", justify="right")
    table.add_column("Tools")

    for s in skills:
        active = "[green]yes[/green]" if s.get("is_active") else "[red]no[/red]"
        tools = ", ".join(s.get("allowed_tools", [])[:3])
        if len(s.get("allowed_tools", [])) > 3:
            tools += "..."
        table.add_row(
            s["code"],
            s["name"],
            active,
            str(s.get("agent_count", 0)),
            tools or "-",
        )

    console.print(table)


@app.command()
def show(code: str = typer.Argument(..., help="Skill code")):
    """Show skill details and content."""
    try:
        skill = api_client.get_skill(code)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]{skill['name']}[/bold] ({skill['code']})\n\n"
        f"{skill.get('description', '')}\n\n"
        f"Active: {'yes' if skill.get('is_active') else 'no'}  |  "
        f"Agents: {skill.get('agent_count', 0)}  |  "
        f"Resources: {len(skill.get('resource_files', []))}\n"
        f"Allowed tools: {', '.join(skill.get('allowed_tools', [])) or 'none'}",
        title=f"Skill: {skill['code']}",
    ))

    body = skill.get("body", "")
    if body:
        console.print()
        console.print(body)


@app.command()
def sync():
    """Sync skills from filesystem to database."""
    try:
        result = api_client.sync_skills()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(
        f"[green]Sync complete:[/green] "
        f"scanned={result.get('scanned', 0)}, "
        f"created={result.get('created', 0)}, "
        f"updated={result.get('updated', 0)}"
    )
