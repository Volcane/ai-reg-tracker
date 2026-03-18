#!/usr/bin/env python3
"""
ARIS — AI Regulation Intelligence System
Main CLI entry point.

Usage:
  python main.py run                          # fetch + summarize (full pipeline)
  python main.py fetch                        # fetch only
  python main.py fetch --source federal       # federal sources only
  python main.py fetch --source PA            # PA state only
  python main.py summarize                    # summarize pending docs
  python main.py report                       # print dashboard
  python main.py report --days 7              # last 7 days
  python main.py report --jurisdiction PA     # PA only
  python main.py report --urgency High        # filter by urgency
  python main.py export --format json         # export to JSON
  python main.py export --format markdown     # export to Markdown
  python main.py watch --interval 24          # run every 24h
  python main.py status                       # show DB stats
"""

import sys
from pathlib import Path

import click
from rich.console import Console

# Ensure project root is on path when run directly
sys.path.insert(0, str(Path(__file__).parent))

console = Console()


@click.group()
def cli():
    """ARIS — AI Regulation Intelligence System\n
    Monitors Federal and state AI legislation, interprets the language,
    and delivers actionable business summaries."""
    pass


# ── run ───────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--days",    default=30,  show_default=True, help="Look back N days for new documents")
@click.option("--limit",   default=50,  show_default=True, help="Max documents to summarize per run")
def run(days, limit):
    """Full pipeline: fetch all sources, then summarize with AI."""
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner, make_progress

    print_banner()
    orchestrator = Orchestrator()

    with make_progress() as progress:
        fetch_task = progress.add_task("Fetching documents…", total=None)
        fetched    = orchestrator.fetch(lookback_days=days)
        progress.update(fetch_task, completed=1, total=1,
                        description=f"Fetched {fetched} new/updated documents")

        summ_task  = progress.add_task(f"Summarizing (up to {limit})…", total=limit)

        def cb(current, total):
            progress.update(summ_task, completed=current, total=total,
                            description=f"Summarizing {current}/{total}…")

        summarized = orchestrator.summarize(limit=limit, progress_callback=cb)
        progress.update(summ_task, completed=summarized, total=summarized,
                        description=f"Summarized {summarized} documents")

    console.print(f"\n[bold green]✓[/bold green] Fetch: {fetched} new   "
                  f"[bold green]✓[/bold green] Summarized: {summarized}")
    console.print("[dim]Run 'python main.py report' to view results.[/dim]")


# ── fetch ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--source",  default=None,
              help="Source to fetch: 'federal', 'state', or a state code like 'PA'")
@click.option("--days",    default=30, show_default=True)
def fetch(source, days):
    """Fetch documents from sources without AI summarization."""
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner, make_progress

    print_banner()
    orchestrator = Orchestrator()
    sources      = [source] if source else None

    with make_progress() as progress:
        task = progress.add_task("Fetching…", total=None)
        count = orchestrator.fetch(sources=sources, lookback_days=days)
        progress.update(task, completed=1, total=1,
                        description=f"Done — {count} new/updated documents")

    console.print(f"\n[bold green]✓[/bold green] Saved {count} new/updated documents to database")


# ── summarize ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--limit", default=50, show_default=True,
              help="Max documents to summarize")
def summarize(limit):
    """Run AI summarization on all pending documents in the database."""
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner, make_progress

    print_banner()
    orchestrator = Orchestrator()

    with make_progress() as progress:
        task = progress.add_task(f"Summarizing (up to {limit})…", total=limit)

        def cb(current, total):
            progress.update(task, completed=current, total=total,
                            description=f"Summarizing {current}/{total}…")

        count = orchestrator.summarize(limit=limit, progress_callback=cb)

    console.print(f"\n[bold green]✓[/bold green] Created {count} AI summaries")


# ── report ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--days",         default=30,   show_default=True)
@click.option("--jurisdiction", default=None, help="Filter by jurisdiction: 'Federal' or state code")
@click.option("--urgency",      default=None,
              type=click.Choice(["Low", "Medium", "High", "Critical"]),
              help="Filter by urgency level")
def report(days, jurisdiction, urgency):
    """Display the AI regulation intelligence dashboard."""
    from utils.reporter import print_report
    print_report(days=days, jurisdiction=jurisdiction, urgency_filter=urgency)


# ── export ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--format", "fmt",
              default="markdown",
              type=click.Choice(["json", "markdown"]),
              show_default=True)
@click.option("--days",    default=30, show_default=True)
@click.option("--output",  default=None, help="Output file path (default: auto-named in ./output/)")
def export(fmt, days, output):
    """Export summaries to JSON or Markdown."""
    from utils.reporter import export_json, export_markdown

    if fmt == "json":
        path = export_json(days=days, filepath=output)
    else:
        path = export_markdown(days=days, filepath=output)

    console.print(f"[bold green]✓[/bold green] Exported to [underline]{path}[/underline]")


# ── status ────────────────────────────────────────────────────────────────────

@cli.command()
def status():
    """Show database statistics and configuration status."""
    from utils.reporter import print_banner, print_stats
    from config.settings import (
        ANTHROPIC_API_KEY, REGULATIONS_GOV_KEY,
        CONGRESS_GOV_KEY, LEGISCAN_KEY
    )
    from config.jurisdictions import ENABLED_US_STATES, ENABLED_INTERNATIONAL

    print_banner()
    print_stats()

    console.print("\n[bold]API Key Status[/bold]")
    keys = {
        "Anthropic (required)":    ANTHROPIC_API_KEY,
        "Regulations.gov":         REGULATIONS_GOV_KEY,
        "Congress.gov":            CONGRESS_GOV_KEY,
        "LegiScan (US states)":    LEGISCAN_KEY,
    }
    for name, key in keys.items():
        icon = "[green]✓[/green]" if key else "[red]✗[/red]"
        console.print(f"  {icon}  {name}")

    console.print(f"\n[bold]Enabled US States[/bold]:     {', '.join(ENABLED_US_STATES) or 'None'}")
    console.print(f"[bold]Enabled International[/bold]: {', '.join(ENABLED_INTERNATIONAL) or 'None'}")


# ── agents ────────────────────────────────────────────────────────────────────

@cli.command()
def agents():
    """List all active source agents by track."""
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner
    print_banner()
    orch   = Orchestrator()
    active = orch.list_active_agents()
    console.print("\n[bold blue]Track 1 — US Federal[/bold blue]")
    for a in active["federal"]:
        console.print(f"  [green]✓[/green]  {a}")
    console.print("\n[bold blue]Track 2 — US States[/bold blue]")
    if active["us_states"]:
        for a in active["us_states"]:
            console.print(f"  [green]✓[/green]  {a}")
    else:
        console.print("  [dim]None enabled[/dim]")
    console.print("\n[bold blue]Track 3 — International[/bold blue]")
    if active["international"]:
        for a in active["international"]:
            console.print(f"  [green]✓[/green]  {a}")
    else:
        console.print("  [dim]None enabled[/dim]")


# ── diff ──────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("doc_id_a")
@click.argument("doc_id_b")
def diff(doc_id_a, doc_id_b):
    """Compare two documents by their database IDs and show what changed.

    Example: python main.py diff FR-2024-00123 FR-2025-00456
    """
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner
    print_banner()

    console.print(f"[dim]Comparing:[/dim] [bold]{doc_id_a}[/bold] → [bold]{doc_id_b}[/bold]\n")
    orch   = Orchestrator()
    result = orch.compare_two_documents(doc_id_a, doc_id_b)

    if not result:
        console.print("[yellow]No substantive differences found, or one/both documents not in database.[/yellow]")
        return

    _print_diff_result(result)


@cli.command()
@click.option("--days",     default=30,   show_default=True)
@click.option("--severity", default=None,
              type=click.Choice(["Low", "Medium", "High", "Critical"]))
@click.option("--type",     "diff_type", default=None,
              type=click.Choice(["version_update", "addendum"]))
@click.option("--unreviewed", is_flag=True, default=False,
              help="Show only diffs not yet marked as reviewed")
def changes(days, severity, diff_type, unreviewed):
    """Show detected regulatory changes — version updates and addenda."""
    from utils.db import get_recent_diffs, get_unreviewed_diffs
    from utils.reporter import print_banner
    print_banner()

    if unreviewed:
        diffs = get_unreviewed_diffs(limit=100)
        console.print(f"[bold]Unreviewed Changes[/bold] ({len(diffs)} pending)\n")
    else:
        diffs = get_recent_diffs(days=days, severity=severity, diff_type=diff_type)
        console.print(f"[bold]Regulatory Changes[/bold] — last {days} days ({len(diffs)} found)\n")

    if not diffs:
        console.print("[dim]No changes found for the specified filters.[/dim]")
        return

    for d in diffs:
        _print_diff_result(d)


@cli.command()
@click.argument("base_id")
@click.argument("addendum_id")
def link(base_id, addendum_id):
    """Manually declare that ADDENDUM_ID amends or clarifies BASE_ID.

    Runs the full addendum analysis and saves the result.

    Example: python main.py link EU-CELEX-32024R1689 EU-AIOFFICE-guidelines-2025
    """
    from agents.orchestrator import Orchestrator
    from utils.reporter import print_banner
    print_banner()

    console.print(f"[dim]Linking addendum:[/dim]\n"
                  f"  Base:     [bold]{base_id}[/bold]\n"
                  f"  Addendum: [bold]{addendum_id}[/bold]\n")

    orch   = Orchestrator()
    result = orch.link_addendum_manually(base_id, addendum_id)

    if not result:
        console.print("[yellow]Could not complete analysis. Check that both document IDs exist in the database.[/yellow]")
        return

    _print_diff_result(result)


@cli.command()
@click.argument("doc_id")
def history(doc_id):
    """Show the full change history for a specific document.

    Example: python main.py history FR-2024-00123
    """
    from utils.db import get_diffs_for_document, get_links_for_document, get_document
    from utils.reporter import print_banner
    print_banner()

    doc = get_document(doc_id)
    if not doc:
        console.print(f"[red]Document not found:[/red] {doc_id}")
        return

    console.print(f"\n[bold]{doc['title']}[/bold]")
    console.print(f"[dim]{doc['jurisdiction']} | {doc['doc_type']} | {doc['status']}[/dim]")
    console.print(f"[dim]{doc['url']}[/dim]\n")

    links = get_links_for_document(doc_id)
    if links:
        console.print(f"[bold blue]Document Relationships[/bold blue] ({len(links)})")
        for lnk in links:
            direction = "← amends" if lnk["related_doc_id"] == doc_id else "→ amends"
            other     = lnk["related_doc_id"] if lnk["base_doc_id"] == doc_id else lnk["base_doc_id"]
            console.print(f"  {direction}  [dim]{other}[/dim]  [{lnk['link_type']}]")

    diffs = get_diffs_for_document(doc_id)
    if diffs:
        console.print(f"\n[bold blue]Change History[/bold blue] ({len(diffs)} events)")
        for d in diffs:
            reviewed = "[green]✓ reviewed[/green]" if d["reviewed"] else "[yellow]⚠ unreviewed[/yellow]"
            console.print(
                f"\n  [{d['detected_at'][:10]}]  "
                f"[bold]{d['severity']}[/bold]  {d['relationship_type'] or d['diff_type']}  {reviewed}"
            )
            console.print(f"  {d['change_summary']}")
            for item in (d.get("new_action_items") or [])[:3]:
                console.print(f"    → {item}")
    else:
        console.print("[dim]No change history found for this document.[/dim]")


@cli.command()
@click.argument("diff_id", type=int)
def review(diff_id):
    """Mark a diff as reviewed by your compliance team.

    Example: python main.py review 42
    """
    from utils.db import mark_diff_reviewed
    mark_diff_reviewed(diff_id)
    console.print(f"[green]✓[/green] Diff ID {diff_id} marked as reviewed.")


# ── Helper: print a diff result to console ────────────────────────────────────

def _print_diff_result(d: dict):
    """Render a single diff result dict to the terminal."""
    severity_style = {
        "Critical": "bold red",
        "High":     "bold yellow",
        "Medium":   "yellow",
        "Low":      "dim green",
    }.get(d.get("severity", "Low"), "")

    diff_id   = d.get("id", "")
    id_str    = f"  [dim]Diff ID: {diff_id}[/dim]" if diff_id else ""
    reviewed  = "  [green]✓ reviewed[/green]" if d.get("reviewed") else "  [yellow]⚠ unreviewed[/yellow]"

    console.print(
        f"[{severity_style}]{d.get('severity','').upper()}[/{severity_style}]  "
        f"[bold]{d.get('relationship_type') or d.get('diff_type','')}[/bold]"
        f"{id_str}{reviewed}"
    )
    console.print(f"  Base:  [dim]{d.get('base_document_id','')[:70]}[/dim]")
    console.print(f"  New:   [dim]{d.get('new_document_id','')[:70]}[/dim]")
    console.print(f"\n  {d.get('change_summary','')}\n")

    added = d.get("added_requirements") or []
    if added:
        console.print("  [bold red]New Requirements Added[/bold red]")
        for r in added:
            desc = r.get("description", r) if isinstance(r, dict) else r
            section = f"  [{r.get('section')}]" if isinstance(r, dict) and r.get("section") else ""
            console.print(f"    + {desc}{section}")

    removed = d.get("removed_requirements") or []
    if removed:
        console.print("  [bold green]Requirements Removed / Relaxed[/bold green]")
        for r in removed:
            desc = r.get("description", r) if isinstance(r, dict) else r
            console.print(f"    - {desc}")

    modified = d.get("modified_requirements") or []
    if modified:
        console.print("  [bold yellow]Modified Requirements[/bold yellow]")
        for r in modified:
            desc      = r.get("description", r) if isinstance(r, dict) else r
            direction = f"  [{r.get('direction')}]" if isinstance(r, dict) and r.get("direction") else ""
            console.print(f"    ~ {desc}{direction}")

    deadlines = d.get("deadline_changes") or []
    if deadlines:
        console.print("  [bold blue]Deadline Changes[/bold blue]")
        for dl in deadlines:
            old = dl.get("old_deadline") or "N/A"
            new = dl.get("new_deadline") or "N/A"
            console.print(f"    {dl.get('description','')}  [{old} → {new}]")

    actions = d.get("new_action_items") or []
    if actions:
        console.print("  [bold]Action Items[/bold]")
        for a in actions:
            console.print(f"    → {a}")

    obsolete = d.get("obsolete_action_items") or []
    if obsolete:
        console.print("  [dim]No Longer Required[/dim]")
        for o in obsolete:
            console.print(f"    ✗ {o}")

    if d.get("overall_assessment"):
        console.print(f"\n  [italic]{d['overall_assessment']}[/italic]")

    console.print()


# ── watch ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--interval", default=24, show_default=True,
              help="Hours between runs")
@click.option("--days",     default=7,  show_default=True,
              help="Lookback window for each run")
def watch(interval, days):
    """Run the pipeline continuously on a schedule (Ctrl+C to stop)."""
    from agents.scheduler import run_watch
    console.print(
        f"[bold]Starting ARIS watch mode[/bold] — "
        f"running every [blue]{interval}h[/blue], "
        f"lookback [blue]{days}d[/blue]"
    )
    run_watch(interval_hours=interval, lookback_days=days)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
