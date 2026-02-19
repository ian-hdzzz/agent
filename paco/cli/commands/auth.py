"""paco auth -- login and credential management."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli import api_client, config

app = typer.Typer(name="auth", help="Authentication and credentials.")
console = Console()


@app.command()
def login(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Account email"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Account password"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Override API base URL"),
):
    """Authenticate with the PACO API and store credentials."""
    if api_url:
        config.set_api_url(api_url)

    if not email:
        email = typer.prompt("Email")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    try:
        data = api_client.login(email, password)
    except api_client.APIError as e:
        console.print(f"[red]Login failed:[/red] {e.detail}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Connection error:[/red] {e}")
        raise typer.Exit(1)

    token = data["token"]
    user = data["user"]

    config.save_credentials(
        access_token=token["access_token"],
        expires_at=token["expires_at"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
    )

    console.print(Panel(
        f"[green]Logged in as[/green] {user['name']} ({user['email']})\n"
        f"Role: [bold]{user['role']}[/bold]\n"
        f"Token expires: {token['expires_at']}",
        title="PACO Auth",
    ))


@app.command()
def status():
    """Show current authentication status."""
    creds = config.load_credentials()
    if not creds:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login' to sign in.")
        raise typer.Exit(1)

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("Email", creds.get("email", "?"))
    table.add_row("Name", creds.get("name", "?"))
    table.add_row("Role", creds.get("role", "?"))
    table.add_row("Expires", creds.get("expires_at", "?"))
    table.add_row("API URL", config.get_api_url())
    console.print(Panel(table, title="Current Session"))


@app.command()
def logout():
    """Clear stored credentials."""
    config.clear_credentials()
    console.print("[green]Logged out.[/green]")


@app.command()
def whoami():
    """Fetch current user info from the API."""
    try:
        user = api_client.get_me()
    except api_client.AuthError:
        console.print("[yellow]Not authenticated.[/yellow] Run 'paco auth login'.")
        raise typer.Exit(1)
    except api_client.APIError as e:
        console.print(f"[red]Error:[/red] {e.detail}")
        raise typer.Exit(1)

    console.print(json.dumps(user, indent=2, default=str))
