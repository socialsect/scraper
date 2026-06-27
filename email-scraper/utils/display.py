"""Rich live dashboard for the email scraper."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Callable, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


class LiveDisplay:
    """
    Thread-safe rich Live dashboard.

    Usage:
        display = LiveDisplay(query="dental clinics london", total_urls=120)
        with display:
            display.update_stats(pages=5, new_emails=3, total_emails=103, ...)
            display.log(\"Found: info@example.com\")
    """

    MAX_LOG_LINES = 14

    def __init__(
        self, 
        query: str, 
        total_urls: int, 
        backend: str = "scrapling",
        on_update: Optional[Callable] = None,
        on_log: Optional[Callable] = None,
    ):
        self._query = query
        self._total_urls = total_urls
        self._backend = backend
        self._start_time = datetime.now()
        self._lock = Lock()
        
        # Callbacks for external integrations (e.g., web dashboard)
        self._on_update = on_update
        self._on_log = on_log

        self._pages = 0
        self._new_emails = 0
        self._total_emails = 0
        self._last_email = ""
        self._queue_size = 0
        self._log_lines: list[str] = []
        self._errors = 0

        self._live = Live(
            self._build_layout(),
            console=console,
            refresh_per_second=4,
            screen=False,
        )

    def __enter__(self):
        self._live.__enter__()
        return self

    def __exit__(self, *args):
        self._live.__exit__(*args)

    # ------------------------------------------------------------------ #
    # Public update methods (thread-safe)                                 #
    # ------------------------------------------------------------------ #

    def update_stats(
        self,
        pages: int | None = None,
        new_emails: int | None = None,
        total_emails: int | None = None,
        last_email: str | None = None,
        queue_size: int | None = None,
    ) -> None:
        with self._lock:
            if pages is not None:
                self._pages = pages
            if new_emails is not None:
                self._new_emails = new_emails
            if total_emails is not None:
                self._total_emails = total_emails
            if last_email is not None:
                self._last_email = last_email
            if queue_size is not None:
                self._queue_size = queue_size
            self._refresh()
            
            # Trigger callback if set
            if self._on_update:
                try:
                    self._on_update(
                        pages=self._pages,
                        new_emails=self._new_emails,
                        total_emails=self._total_emails,
                        last_email=self._last_email,
                        queue_size=self._queue_size,
                        errors=self._errors,
                    )
                except Exception as e:
                    print(f"[LiveDisplay] Callback error: {e}")

    def log(self, message: str) -> None:
        with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_lines.append(f"[dim]{ts}[/dim]  {message}")
            if len(self._log_lines) > self.MAX_LOG_LINES:
                self._log_lines = self._log_lines[-self.MAX_LOG_LINES :]
            self._refresh()
            
            # Trigger callback if set
            if self._on_log:
                try:
                    self._on_log(f"{ts} | {message}")
                except Exception as e:
                    print(f"[LiveDisplay] Log callback error: {e}")

    def log_error(self, message: str) -> None:
        with self._lock:
            self._errors += 1
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_lines.append(f"[dim]{ts}[/dim]  [red]✗[/red] {message}")
            if len(self._log_lines) > self.MAX_LOG_LINES:
                self._log_lines = self._log_lines[-self.MAX_LOG_LINES :]
            self._refresh()
            
            # Trigger callback if set
            if self._on_log:
                try:
                    self._on_log(f"{ts} | ERROR: {message}")
                except Exception as e:
                    print(f"[LiveDisplay] Log callback error: {e}")

    # ------------------------------------------------------------------ #
    # Internal rendering                                                  #
    # ------------------------------------------------------------------ #

    def _elapsed(self) -> str:
        delta = datetime.now() - self._start_time
        total_seconds = int(delta.total_seconds())
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m:02d}m {s:02d}s"
        return f"{m:02d}m {s:02d}s"

    def _rate(self) -> str:
        delta = (datetime.now() - self._start_time).total_seconds()
        if delta < 1 or self._new_emails == 0:
            return "—"
        rate = self._new_emails / delta * 60
        return f"{rate:.1f}/min"

    def _build_stats_table(self) -> Table:
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="bold cyan", no_wrap=True)
        table.add_column(style="white")

        table.add_row("Query", f"[yellow]{self._query}[/yellow]")
        table.add_row("Backend", f"[magenta]{self._backend}[/magenta]")
        table.add_row("Elapsed", self._elapsed())
        table.add_row("URLs queued", f"{self._queue_size:,}")
        table.add_row("Pages crawled", f"[green]{self._pages:,}[/green]")
        table.add_row("Emails this run", f"[bold green]{self._new_emails:,}[/bold green]")
        table.add_row("Total in CSV", f"[bold white]{self._total_emails:,}[/bold white]")
        table.add_row("Rate", self._rate())
        table.add_row("Errors", f"[red]{self._errors}[/red]" if self._errors else "0")
        if self._last_email:
            table.add_row("Last saved", f"[dim]{self._last_email[:60]}[/dim]")

        return table

    def _build_log_panel(self) -> Panel:
        log_text = Text.from_markup("\n".join(self._log_lines) or "[dim]Waiting...[/dim]")
        return Panel(log_text, title="[bold]Activity[/bold]", border_style="dim", padding=(0, 1))

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="stats", size=14),
            Layout(name="log"),
        )
        layout["stats"].update(
            Panel(self._build_stats_table(), title="[bold cyan]Email Scraper[/bold cyan]", border_style="cyan")
        )
        layout["log"].update(self._build_log_panel())
        return layout

    def _refresh(self) -> None:
        self._live.update(self._build_layout())
