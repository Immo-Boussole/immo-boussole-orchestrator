"""
Immo-Boussole Orchestrator CLI.

All commands call the orchestrator REST API (default http://localhost:9000)
so the CLI stays in sync with the web UI.

Usage:
    python -m cli.main --help
    python -m cli.main list
    python -m cli.main start dev
    python -m cli.main logs prod --follow
"""
from __future__ import annotations

import json
import os
import webbrowser
from typing import Optional

import httpx
import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="orchestrator",
    help="🎛️  Immo-Boussole Orchestrator CLI",
    rich_markup_mode="rich",
)
console = Console()

# ── Config ────────────────────────────────────────────────────────────────────

def _api_url() -> str:
    return os.environ.get("ORCHESTRATOR_API_URL", "http://localhost:9000")


def _auth() -> tuple[str, str]:
    username = os.environ.get("ORCHESTRATOR_USER", "admin")
    password = os.environ.get("ORCHESTRATOR_PASSWORD", "admin")
    return (username, password)


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=_api_url(),
        auth=_auth(),
        timeout=60,
    )


def _handle_error(resp: httpx.Response) -> None:
    if not resp.is_success:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        console.print(f"[bold red]Error {resp.status_code}:[/bold red] {detail}")
        raise typer.Exit(code=1)


# ── list ──────────────────────────────────────────────────────────────────────

@app.command("list")
def list_instances():
    """List all registered Immo-Boussole instances with their status."""
    with _client() as client:
        resp = client.get("/api/instances")
        _handle_error(resp)
        data = resp.json()

    if not data:
        console.print("[dim]No instances registered.[/dim]")
        return

    table = Table(title="🎛️  Immo-Boussole Instances", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold white", no_wrap=True)
    table.add_column("Host", style="dim")
    table.add_column("Port", justify="right")
    table.add_column("Image", max_width=35)
    table.add_column("State", justify="center")
    table.add_column("Uptime")

    state_icons = {
        "running": "[green]🟢 running[/green]",
        "exited":  "[red]🔴 exited[/red]",
        "stopped": "[red]🔴 stopped[/red]",
        "absent":  "[dim]⚪ absent[/dim]",
        "error":   "[red]⚠️  error[/red]",
        "unhealthy": "[yellow]🟡 unhealthy[/yellow]",
    }

    for item in data:
        cfg = item["config"]
        st  = item["status"]
        state = st.get("state", "unknown")
        icon = state_icons.get(state, f"[dim]{state}[/dim]")

        uptime = "—"
        secs = st.get("uptime_seconds")
        if secs is not None:
            if secs < 60:         uptime = f"{secs}s"
            elif secs < 3600:     uptime = f"{secs//60}m"
            elif secs < 86400:    uptime = f"{secs//3600}h {(secs%3600)//60}m"
            else:                 uptime = f"{secs//86400}d {(secs%86400)//3600}h"

        table.add_row(
            cfg["name"],
            cfg["host"],
            str(cfg["port"]),
            cfg.get("image") or "(local build)",
            icon,
            uptime,
        )

    console.print(table)


# ── status ────────────────────────────────────────────────────────────────────

@app.command()
def status(name: str = typer.Argument(..., help="Instance name")):
    """Show detailed status of a single instance."""
    with _client() as client:
        resp = client.get(f"/api/instances/{name}")
        _handle_error(resp)
        data = resp.json()

    cfg = data["config"]
    st  = data["status"]

    console.rule(f"[bold]{name}[/bold]")
    console.print(f"  [dim]Host :[/dim]  {cfg['host']}")
    console.print(f"  [dim]Port :[/dim]  {cfg['port']}")
    console.print(f"  [dim]Image:[/dim]  {cfg.get('image') or '(local build)'}")
    console.print(f"  [dim]State:[/dim]  {st['state']}")
    console.print(f"  [dim]Health:[/dim] {st['health']}")
    if st.get("uptime_seconds") is not None:
        console.print(f"  [dim]Uptime:[/dim] {st['uptime_seconds']}s")
    if st.get("error"):
        console.print(f"  [red]Error:[/red]  {st['error']}")
    if cfg.get("description"):
        console.print(f"  [dim]Desc :[/dim]  {cfg['description']}")


# ── add ───────────────────────────────────────────────────────────────────────

@app.command()
def add(
    name:          str           = typer.Option(..., "--name", "-n",  help="Instance name"),
    host:          str           = typer.Option("local", "--host",     help="Docker host connection string"),
    port:          int           = typer.Option(8000,   "--port", "-p", help="Host port"),
    image:         Optional[str] = typer.Option("wikijm/immo-boussole:latest", "--image", "-i", help="Docker image"),
    env_file:      Optional[str] = typer.Option(None,  "--env-file",   help="Path to .env file"),
    build_context: Optional[str] = typer.Option(None,  "--build",      help="Local build context directory"),
    description:   str           = typer.Option("",    "--description", "-d", help="Human-readable description"),
    start:         bool          = typer.Option(False, "--start",       help="Start container immediately"),
):
    """Register a new Immo-Boussole instance."""
    payload = {
        "name": name, "host": host, "port": port, "image": image,
        "env_file": env_file, "build_context": build_context,
        "description": description, "start_after_create": start,
    }
    with _client() as client:
        resp = client.post("/api/instances", json=payload)
        _handle_error(resp)
    console.print(f"[green]✔[/green] Instance [bold]{name}[/bold] registered.")
    if start:
        console.print(f"  [dim]Container start requested.[/dim]")


# ── start / stop / restart ────────────────────────────────────────────────────

def _lifecycle(name: str, action: str, icon: str, colour: str):
    with _client() as client:
        resp = client.post(f"/api/instances/{name}/{action}")
        _handle_error(resp)
    console.print(f"[{colour}]{icon}[/{colour}] Instance [bold]{name}[/bold] {action}ed.")


@app.command()
def start(name: str = typer.Argument(...)):
    """Start a stopped instance."""
    _lifecycle(name, "start", "▶", "green")


@app.command()
def stop(name: str = typer.Argument(...)):
    """Stop a running instance."""
    _lifecycle(name, "stop", "⏹", "yellow")


@app.command()
def restart(name: str = typer.Argument(...)):
    """Restart an instance."""
    _lifecycle(name, "restart", "🔄", "cyan")


# ── update ────────────────────────────────────────────────────────────────────

@app.command()
def update(
    name: str           = typer.Argument(...),
    tag:  Optional[str] = typer.Option(None, "--tag", "-t", help="Image tag to deploy"),
):
    """Pull latest image (or a specific tag) and recreate the container."""
    payload = {"tag": tag} if tag else None
    with _client() as client:
        resp = client.post(f"/api/instances/{name}/update", json=payload)
        _handle_error(resp)
    console.print(f"[green]⬆[/green] Instance [bold]{name}[/bold] updated (tag={tag or 'latest'}).")


# ── remove ────────────────────────────────────────────────────────────────────

@app.command()
def remove(
    name:         str  = typer.Argument(...),
    keep_volumes: bool = typer.Option(True,  "--keep-volumes/--delete-volumes",
                                     help="Keep or delete Docker volumes"),
    yes:          bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Remove an instance (container + registry entry)."""
    if not yes:
        confirm = typer.confirm(
            f"Delete instance '{name}'? "
            f"{'Volumes will be kept.' if keep_volumes else '⚠️  Volumes will also be deleted!'}"
        )
        if not confirm:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    with _client() as client:
        resp = client.delete(f"/api/instances/{name}?keep_volumes={str(keep_volumes).lower()}")
        _handle_error(resp)
    console.print(f"[red]🗑[/red] Instance [bold]{name}[/bold] deleted.")


# ── clone ─────────────────────────────────────────────────────────────────────

@app.command()
def clone(
    source:      str = typer.Argument(..., help="Source instance name"),
    target_name: str = typer.Argument(..., help="New instance name"),
    target_port: int = typer.Option(..., "--port", "-p", help="Port for the new instance"),
    target_host: str = typer.Option("local", "--host",  help="Docker host for the new instance"),
):
    """Clone an instance's config to a new instance."""
    payload = {"target_name": target_name, "target_port": target_port, "target_host": target_host}
    with _client() as client:
        resp = client.post(f"/api/instances/{source}/clone", json=payload)
        _handle_error(resp)
    console.print(f"[green]✔[/green] Cloned [bold]{source}[/bold] → [bold]{target_name}[/bold].")


# ── logs ──────────────────────────────────────────────────────────────────────

@app.command()
def logs(
    name:   str  = typer.Argument(...),
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream logs in real time"),
    tail:   int  = typer.Option(100,  "--tail",  "-n",  help="Number of lines to show"),
):
    """Show container logs for an instance."""
    if follow:
        console.print(f"[dim]Streaming logs for [bold]{name}[/bold]… (Ctrl+C to stop)[/dim]")
        import urllib.request
        url = f"{_api_url()}/api/instances/{name}/logs/stream"
        req = urllib.request.Request(url)
        import base64
        user, pwd = _auth()
        creds = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
        try:
            with urllib.request.urlopen(req) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line.startswith("data: "):
                        console.print(line[6:])
        except KeyboardInterrupt:
            console.print("\n[dim]Stream stopped.[/dim]")
    else:
        with _client() as client:
            resp = client.get(f"/api/instances/{name}/logs?tail={tail}")
            _handle_error(resp)
        data = resp.json()
        for line in data.get("lines", []):
            console.print(line)


# ── backup / restore ──────────────────────────────────────────────────────────

@app.command()
def backup(name: str = typer.Argument(...)):
    """Trigger a backup of the instance via its Immo-Boussole API."""
    with _client() as client:
        resp = client.post(f"/api/instances/{name}/backup")
        _handle_error(resp)
    data = resp.json()
    console.print(f"[green]💾[/green] Backup triggered for [bold]{name}[/bold].")
    if data.get("detail"):
        console.print(json.dumps(data["detail"], indent=2))


@app.command()
def restore(
    name: str = typer.Argument(...),
    file: str = typer.Option(..., "--file", "-f", help="Path to the backup archive"),
):
    """Trigger a restore of the instance from a backup archive."""
    with _client() as client:
        resp = client.post(f"/api/instances/{name}/restore", json={"archive_path": file})
        _handle_error(resp)
    console.print(f"[green]✔[/green] Restore triggered for [bold]{name}[/bold].")


# ── ui ────────────────────────────────────────────────────────────────────────

@app.command()
def ui():
    """Open the orchestrator web UI in the default browser."""
    url = _api_url()
    console.print(f"[dim]Opening [/dim][link={url}]{url}[/link]")
    webbrowser.open(url)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
