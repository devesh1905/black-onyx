"""Terminal replay fallback for Black Onyx event logs using Rich.

Usage:
    python demo/replay.py runs/example.jsonl
    python demo/replay.py runs/example.jsonl --delay 0.5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()



def format_trust(trust: str) -> Text:
    if trust == "USER":
        return Text(trust, style="bold green")
    elif trust == "VERIFIED":
        return Text(trust, style="bold blue")
    elif trust == "UNTRUSTED":
        return Text(trust, style="bold #f97316")  # Orange
    return Text(trust, style="dim")


def replay_event(ev: dict[str, Any], console: Console) -> None:
    etype = ev.get("type", "unknown")
    seq = ev.get("seq", 0)
    ts = ev.get("ts", 0.0)

    prefix = f"[dim]#{seq:02d} ({ts:.3f}s)[/dim]"

    if etype == "request":
        console.print()
        console.print(
            Panel(
                f"[bold green]USER REQUEST ({ev.get('task_id', 'REQ')})[/bold green]\n"
                f"[white]{ev.get('text')}[/white]\n\n"
                f"[dim]Defence: {ev.get('defence', 'D3')}[/dim]",
                title=f"{prefix} Request",
                border_style="green",
            )
        )

    elif etype == "plan":
        table = Table(title=f"{prefix} Execution Plan", border_style="cyan", show_header=True)
        table.add_column("Call ID", style="bold cyan", width=10)
        table.add_column("Tool", style="yellow", width=18)
        table.add_column("Description", style="white")
        for s in ev.get("steps", []):
            table.add_row(s.get("call_id", ""), s.get("tool", ""), s.get("desc", ""))
        console.print(table)

    elif etype == "tool_result":
        trust_str = ev.get("trust", "UNTRUSTED")
        color = "green" if trust_str == "USER" else ("blue" if trust_str == "VERIFIED" else "#f97316")
        sources_str = ", ".join(ev.get("sources", []))
        console.print(
            Panel(
                f"[bold]Tool:[/bold] {ev.get('tool')} ([cyan]{ev.get('call_id')}[/cyan])\n"
                f"[bold]Value:[/bold] [bold {color}]{ev.get('value_id')}[/bold {color}]  "
                f"[bold]Trust:[/bold] [{color}]{trust_str}[/{color}]  "
                f"[bold]Sources:[/bold] [dim]{sources_str}[/dim]\n"
                f"[bold]Preview:[/bold] [italic]\"{ev.get('preview')}\"[/italic]",
                title=f"{prefix} Tool Result -> {ev.get('value_id')}",
                border_style=color,
            )
        )

    elif etype == "op":
        trust_str = ev.get("trust", "UNTRUSTED")
        color = "green" if trust_str == "USER" else ("blue" if trust_str == "VERIFIED" else "#f97316")
        ins = ", ".join(ev.get("inputs", []))
        console.print(
            f"{prefix} [dim]op:[/dim] [bold cyan]{ev.get('op')}[/bold cyan]({ins}) -> "
            f"[{color}]{ev.get('output')} [{trust_str}][/{color}] "
            f"[dim]\"{ev.get('preview')}\"[/dim]"
        )

    elif etype == "declassify":
        console.print(
            Panel(
                f"[bold blue]Declassified by validator:[/bold blue] [cyan]{ev.get('validator')}[/cyan]\n"
                f"[bold]Input:[/bold] {ev.get('input')} -> [bold blue]{ev.get('output')} [VERIFIED][/bold blue]\n"
                f"[bold]Rule:[/bold] {ev.get('rule')}\n"
                f"[bold]Preview:[/bold] \"{ev.get('preview')}\"",
                title=f"{prefix} Declassify Validator",
                border_style="blue",
            )
        )

    elif etype == "call_check":
        decision = ev.get("decision", "allow")
        cid = ev.get("call_id")
        tool = ev.get("tool")
        arg = ev.get("argument")
        vid = ev.get("value_id")
        reason = ev.get("reason", "")

        if decision == "deny":
            console.print(
                Panel(
                    f"[bold red]⛔ CALL CHECK DENIED[/bold red]\n"
                    f"[bold]Target Tool:[/bold] {tool}.{arg} (Call ID: {cid})\n"
                    f"[bold]Argument Value:[/bold] {vid} ([bold #f97316]{ev.get('trust')}[/bold #f97316])\n"
                    f"[bold]Policy Reason:[/bold] {reason}",
                    title=f"{prefix} Policy Gate Block",
                    border_style="bold red",
                )
            )
        else:
            console.print(
                f"{prefix} [bold green]✓ CALL CHECK ALLOWED:[/bold green] "
                f"[white]{tool}.{arg}[/white] ({vid}) [dim]{reason}[/dim]"
            )

    elif etype == "alert":
        console.print()
        console.print(
            Panel(
                f"[bold red]🚨 SECURITY ALERT - ATTACK BLOCKED 🚨[/bold red]\n\n"
                f"[bold]Attempted Call:[/bold] {ev.get('tool')} ([cyan]{ev.get('call_id')}[/cyan])\n"
                f"[bold]Violation:[/bold] {ev.get('reason')}\n\n"
                f"[bold underline]Provenance Chain:[/bold underline]\n"
                f"[bold yellow]{ev.get('chain')}[/bold yellow]",
                title=f"[blink bold red]CRITICAL ALERT[/blink bold red] - {prefix}",
                border_style="bold red",
                style="on #2a0808",
            )
        )
        console.print()

    elif etype == "laya_score":
        score = ev.get("score")
        ms = ev.get("ms", 0.0)
        warn = ev.get("warn", False)
        status_txt = "[bold red]⚠️ LOW FIT (WARNING)[/bold red]" if warn else "[bold green]✓ CALL FITS TASK[/bold green]"
        score_val = f"{score:.3f}" if score is not None else "n/a"
        console.print(
            f"{prefix} [magenta]Laya Sentinel ({ev.get('call_id')}):[/magenta] "
            f"score={score_val} ({ms:.1f}ms) -> {status_txt}"
        )

    elif etype == "effect":
        console.print(
            Panel(
                f"[bold purple]🎉 EXTERNAL EFFECT PRODUCED[/bold purple]\n"
                f"[bold]Kind:[/bold] {ev.get('kind')} (Call ID: {ev.get('call_id')})\n"
                f"[bold]Description:[/bold] {ev.get('description')}",
                title=f"{prefix} Effect Emitted",
                border_style="purple",
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Terminal replay for Black Onyx JSONL event logs.")
    parser.add_argument(
        "log_path",
        nargs="?",
        default="runs/example.jsonl",
        help="Path to JSONL event log (default: runs/example.jsonl)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Seconds to pause between events. If omitted, prompts for Enter.",
    )
    args = parser.parse_args()

    path = Path(args.log_path)
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] Log file '{path}' not found.")
        sys.exit(1)

    console.print(Panel(f"[bold white]Black Onyx Event Replay[/bold white]\n[dim]{path}[/dim]", border_style="cyan"))

    count = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception as e:
                console.print(f"[red]Error parsing JSON on line: {e}[/red]")
                continue

            count += 1
            replay_event(ev, console)

            if args.delay is not None:
                time.sleep(args.delay)
            else:
                try:
                    input("Press [Enter] for next event...")
                except (KeyboardInterrupt, EOFError):
                    console.print("\n[yellow]Replay aborted by user.[/yellow]")
                    break

    console.print()
    console.print(f"[bold green]Replay completed ({count} events).[/bold green]")


if __name__ == "__main__":
    main()
