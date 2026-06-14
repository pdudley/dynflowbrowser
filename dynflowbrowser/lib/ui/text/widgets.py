"""Custom Textual widgets for Dynflow TUI."""
import json
import os
from rich.align import Align
from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import DataTable
from textual.widgets import Static

from dynflowbrowser.lib.ui.shared import ActionHierarchy
from dynflowbrowser.lib.ui.shared import ActionQueries
from dynflowbrowser.lib.ui.shared import FormatHelpers
from dynflowbrowser.lib.ui.shared import StatsQueries
from .theme import COLORS, STYLES


class AppHeader(Static):
    """Custom application header with styled title."""

    def render(self) -> Text:
        """Render the header with bold orange title.

        Returns:
            Text: Styled header text
        """
        text = Text()
        text.append("DynflowBrowser", style=f"bold {COLORS['brand_orange']}")
        return text


class AppHeaderWithSeparator(Static):
    """Container for app header with separator line."""

    DEFAULT_CSS = """
    AppHeaderWithSeparator {
        height: auto;
        dock: top;
    }

    AppHeaderWithSeparator > Static {
        height: 1;
    }
    """

    def compose(self):
        """Compose header with title and separator."""
        from dynflowbrowser.lib.configuration import get_version
        version = get_version()

        yield AppHeader()
        yield HeaderSeparator(version=version)


def format_date(date_str):
    """Format date to YYYY-MM-DD HH:MM:SS (19 chars).

    Args:
        date_str: Date string in format YYYY-MM-DD HH:MM:SS.microseconds

    Returns:
        str: Formatted date or empty string
    """
    if not date_str:
        return ""
    date_str = str(date_str)
    # Format: 2026-05-22 08:58:14.123456 -> 2026-05-22 08:58:14
    if len(date_str) >= 19:
        # Extract YYYY-MM-DD HH:MM:SS
        return date_str[0:10] + " " + date_str[11:19]
    return date_str


class LogoBanner(Static):
    """ASCII art logo with version, centered with colored background."""

    DEFAULT_CSS = """
    LogoBanner {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 0 2;
    }
    """

    ASCII_ART = """
    ____              ______              ____
   / __ \\__  ______  / __/ /___ _      __/ __ )_________ _      __________  _____
  / / / / / / / __ \\/ /_/ / __ \\ | /| / / __  / ___/ __ \\ | /| / / ___/ _ \\/ ___/
 / /_/ / /_/ / / / / __/ / /_/ / |/ |/ / /_/ / /  / /_/ / |/ |/ (__  )  __/ /
/_____/\\__, /_/ /_/_/ /_/\\____/|__/|__/_____/_/   \\____/|__/|__/____/\\___/_/
      /____/"""

    def __init__(self, **kwargs):
        """Initialize logo banner."""
        super().__init__(**kwargs)
        # Get version using shared method
        from dynflowbrowser.lib.configuration import get_version
        self.version = get_version()

    def render(self) -> RenderableType:
        """Render centered ASCII art with version.

        Returns:
            RenderableType: Centered content
        """
        from rich.console import Group

        # Create version text aligned to the right of the ASCII art
        # The ASCII art width is about 85 chars, version goes at the end
        version_line = " " * 73 + self.version
        version_text = Text(version_line, style=f"dim {COLORS['brand_orange']}")

        # Create text with ASCII art
        art_text = Text(self.ASCII_ART, style=f"bold {COLORS['brand_orange']}")

        # Center both
        centered_version = Align.center(version_text)
        centered_art = Align.center(art_text)

        # Combine with spacing - version before art
        return Group(
            "",
            centered_version,
            centered_art,
            ""
        )


class HeaderSeparator(Static):
    """Orange separator line below header."""

    def __init__(self, version: str = "0", **kwargs):
        """Initialize header separator.

        Args:
            version: Version string
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.version = version.strip() if version else "0"

    def render(self) -> Text:
        """Render the separator line with version on the right.

        Returns:
            Text: Orange horizontal line with version
        """
        # Get terminal width (no horizontal padding)
        try:
            width = self.app.size.width if hasattr(self, 'app') else 120
        except:
            width = 120

        # Build: ─────── {version} ──
        # Format: dashes + space + version + space + 2 end dashes
        version_text = f" {self.version} "
        end_dashes = "──"
        remaining = width - len(version_text) - len(end_dashes)
        if remaining < 0:
            remaining = 0

        text = Text()
        text.append("─" * remaining, style=f"bold {COLORS['brand_orange']}")
        text.append(version_text, style=f"dim {COLORS['brand_orange']}")  # Lighter color
        text.append(end_dashes, style=f"bold {COLORS['brand_orange']}")
        return text


class HostDetailsHeader(Static):
    """Display host details header similar to HTML output."""

    def __init__(self, sos_info):
        """Initialize host details header.

        Args:
            sos_info: Dictionary with system information
        """
        super().__init__()
        self.sos_info = sos_info

    def render(self) -> str:
        """Render the host information.

        Returns:
            str: Formatted host information
        """
        hostname = self.sos_info.get('hostname', 'N/A')
        satversion = self.sos_info.get('satversion', 'N/A')
        timezone = self.sos_info.get('timezone', 'N/A')
        tuning = self.sos_info.get('tuning', 'N/A').strip()
        cpu = self.sos_info.get('cpu', 'N/A')
        ram = self.sos_info.get('ram', 'N/A')

        # Extract RAM values - format is "Physical: XG / Swap: YG"
        # Compact to "XG / YG"
        ram_compact = ram
        if "Physical:" in ram and "Swap:" in ram:
            parts = ram.replace("Physical:", "").replace("Swap:", "").strip()
            ram_compact = parts.replace("  ", " ")

        # Split into two lines
        line1 = (
            f"[{COLORS['accent']}]Host:[/] {hostname} | "
            f"[{COLORS['accent']}]Ver:[/] {satversion} | "
            f"[{COLORS['accent']}]TZ:[/] {timezone}"
        )
        line2 = (
            f"[{COLORS['accent']}]Tuning:[/] {tuning} | "
            f"[{COLORS['accent']}]CPU:[/] {cpu} | "
            f"[{COLORS['accent']}]RAM:[/] {ram_compact}"
        )
        return f"{line1}\n{line2}"


class StatsPanel(Static):
    """Panel showing Top Dynflow Steps and Top Pulp Tasks."""

    def __init__(self, db, conf, **kwargs):
        """Initialize stats panel.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf

    def on_mount(self) -> None:
        """Load and display stats when mounted."""
        self.update_stats()

    def update_stats(self) -> None:
        """Update the stats display."""
        from rich.console import Group
        from dynflowbrowser.lib.util import Util

        util = Util('W')

        # Get top Dynflow steps using shared query (respects filters)
        dynflow_stats = StatsQueries.get_dynflow_total_exectime(
            self.db, self.conf
        )

        # Create Rich table for Dynflow
        dynflow_table = Table(
            title=f"[{STYLES['bold']}]Top Dynflow[/]",
            show_header=True,
            header_style=STYLES["section_title"],
            expand=False,
            box=None
        )
        dynflow_table.add_column("Exectime", justify="right", no_wrap=True)
        dynflow_table.add_column("Steps", justify="right", no_wrap=True)
        dynflow_table.add_column("Label", style=STYLES["dim"], no_wrap=True, overflow="ellipsis")

        for row in dynflow_stats:
            exec_time = f"{float(row[0]):.0f}" if row[0] else "0"
            steps = str(row[1]) if row[1] else "0"
            label = str(row[2]) if row[2] else "N/A"
            dynflow_table.add_row(exec_time, steps, label)

        # Get Pulp data from all action outputs using shared query
        pulp_stats = {}
        actions = StatsQueries.get_all_actions_with_pulp(self.db)

        for action in actions:
            output = action[0]
            pulp_tasks = FormatHelpers.parse_pulp_tasks(output)

            for task in pulp_tasks:
                # Skip tasks without finished_at (pending/running tasks)
                if 'finished_at' not in task or not task['finished_at']:
                    continue
                if 'pulp_created' not in task or not task['pulp_created']:
                    continue

                task_name = task.get('name', 'Unknown')
                finished = util.date_from_string(task['finished_at'])
                created = util.date_from_string(task['pulp_created'])
                exec_time = (finished - created).total_seconds()

                if task_name not in pulp_stats:
                    pulp_stats[task_name] = [0, 0]
                pulp_stats[task_name][0] += exec_time
                pulp_stats[task_name][1] += 1

        # Create Pulp table
        pulp_table = Table(
            title=f"[{STYLES['bold']}]Top Pulp[/]",
            show_header=True,
            header_style=STYLES["section_title"],
            expand=False,
            box=None
        )
        pulp_table.add_column("Exectime", justify="right", no_wrap=True)
        pulp_table.add_column("Count", justify="right", no_wrap=True)
        pulp_table.add_column("Name", style=STYLES["dim"], no_wrap=True, overflow="ellipsis")

        # Sort and show top 5 Pulp tasks
        if pulp_stats:
            sorted_pulp = sorted(
                pulp_stats.items(),
                key=lambda x: x[1][0],
                reverse=True
            )[:5]

            for task_name, (exec_time, count) in sorted_pulp:
                pulp_table.add_row(
                    f"{exec_time:.0f}",
                    str(count),
                    task_name
                )
        else:
            pulp_table.add_row("-", "-", "No Pulp data")

        # Combine both tables
        group = Group(dynflow_table, "", pulp_table)
        self.update(group)


class TasksDataTable(DataTable):
    """DataTable widget for displaying tasks with parent/child hierarchy."""

    def __init__(self, db, conf, **kwargs):
        """Initialize tasks data table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        # Detect database type once
        self.is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )
        self.cursor_type = "row"
        self.zebra_stripes = True
        # Store mapping of row keys to plan UUIDs for navigation
        self.row_to_plan = {}
        # Store ordered list of row keys
        self.row_keys = []
        # Track expanded parent tasks
        self.expanded_parents = set()
        # Store all parent and child task data
        self.parent_tasks = []
        self.children_by_parent = {}
        # Track column display mode (False = Action/ID, True = Label/UUID)
        self.show_label_mode = False

    def on_mount(self) -> None:
        """Load and display tasks data when widget is mounted."""
        self._add_columns()
        # Load task data
        self._load_tasks()

    def _add_columns(self) -> None:
        """Add columns to the table based on current mode."""
        # Add columns - Result and State first, dates use 4-digit year format
        self.add_column("Result", key="result", width=None)
        self.add_column("State", key="state", width=None)
        self.add_column(
            "Task Action" if not self.show_label_mode else "Task Label",
            key="label",
            width=None  # Auto-width to show full content
        )
        self.add_column(
            "Task ID" if not self.show_label_mode else "Plan UUID",
            key="task_id",
            width=36
        )
        self.add_column("Started At", key="started", width=19)
        self.add_column("Ended At", key="ended", width=19)

    def _load_tasks(self) -> None:
        """Load tasks from database."""
        if self.is_postgres:
            self._load_tasks_postgres()
        else:
            self._load_tasks_sqlite()

        # Group children by parent task ID (common for both)
        for child in self.child_tasks_raw:
            parent_id = str(child[0]) if child[0] else ""
            if parent_id and parent_id not in self.children_by_parent:
                self.children_by_parent[parent_id] = []
            if parent_id:
                self.children_by_parent[parent_id].append(child)

        # Initially expand all parents (default behavior)
        for parent in self.parent_tasks:
            parent_id = str(parent[1]) if parent[1] else ""
            if parent_id in self.children_by_parent:
                self.expanded_parents.add(parent_id)

        # Render the table
        self._render_table()

    def _load_tasks_postgres(self) -> None:
        """Load tasks from PostgreSQL database."""
        where = "" if self.conf.args.showall else " AND t.result != 'success'"

        # Fetch parent tasks
        parent_query = """
            SELECT t.parent_task_id, t.id, t.external_id,
                   t.label, t.state, t.result, t.started_at,
                   t.ended_at, t.action, p.state, p.result
            FROM foreman_tasks_tasks t
            LEFT JOIN dynflow_execution_plans p
                ON NULLIF(t.external_id, '')::uuid = p.uuid
            WHERE t.parent_task_id IS NULL
        """ + where + " ORDER BY t.started_at DESC"

        self.parent_tasks = self.db.query(parent_query)

        # Fetch child tasks
        child_query = """
            SELECT t.parent_task_id, t.id, t.external_id,
                   t.label, t.state, t.result, t.started_at,
                   t.ended_at, t.action
            FROM foreman_tasks_tasks t
            LEFT JOIN dynflow_execution_plans p
                ON NULLIF(t.external_id, '')::uuid = p.uuid
            WHERE t.parent_task_id IS NOT NULL
        """ + where + " ORDER BY t.started_at ASC"

        self.child_tasks_raw = self.db.query(child_query)

    def _load_tasks_sqlite(self) -> None:
        """Load tasks from SQLite database."""
        where = "" if self.conf.args.showall else " AND t.result != 'success'"

        # Fetch parent tasks
        parent_query = """
            SELECT t.parent_task_id, t.id, t.external_id,
                   t.label, t.state, t.result, t.started_at,
                   t.ended_at, t.action, p.state, p.result
            FROM foreman_tasks_tasks t
            LEFT JOIN dynflow_execution_plans p
                ON t.external_id = p.uuid
            WHERE t.parent_task_id = ''
        """ + where + " ORDER BY t.started_at DESC"

        self.parent_tasks = self.db.query(parent_query)

        # Fetch child tasks
        child_query = """
            SELECT t.parent_task_id, t.id, t.external_id,
                   t.label, t.state, t.result, t.started_at,
                   t.ended_at, t.action
            FROM foreman_tasks_tasks t
            LEFT JOIN dynflow_execution_plans p
                ON t.external_id = p.uuid
            WHERE t.parent_task_id != ''
        """ + where + " ORDER BY t.started_at ASC"

        self.child_tasks_raw = self.db.query(child_query)

    def _render_table(self) -> None:
        """Render all tasks based on expanded state."""
        # Clear current rows
        self.clear()
        self.row_keys.clear()
        self.row_to_plan.clear()

        # Add rows: parents and their children if expanded
        for parent in self.parent_tasks:
            parent_id = str(parent[1]) if parent[1] else ""
            has_children = parent_id in self.children_by_parent

            # Add parent task
            self._add_task_row(parent, is_child=False, has_children=has_children)

            # Add child tasks if expanded
            if parent_id in self.expanded_parents and has_children:
                for child in self.children_by_parent[parent_id]:
                    self._add_task_row(child, is_child=True)

    def _add_task_row(self, row, is_child=False, has_children=False):
        """Add a task row to the table.

        Args:
            row: Database row with task data
            is_child: If True, indent to show as child task
            has_children: If True, show expand/collapse indicator
        """
        task_id = str(row[1]) if row[1] else ""
        plan_uuid = str(row[2])[:36] if row[2] else ""
        label = str(row[3]) if row[3] else ""
        state = str(row[4]) if row[4] else ""
        result = str(row[5]) if row[5] else ""
        # Format dates as YY-MM-DD HH:MM:SS (17 chars)
        started = format_date(row[6])
        ended = format_date(row[7])
        action = str(row[8]) if row[8] else ""

        # Format first column (action or label depending on mode)
        display_text = label if self.show_label_mode else action
        if is_child:
            label_text = Text()
            label_text.append("  └─ ", style=STYLES["dim"])
            label_text.append(display_text if display_text else "")
        else:
            label_text = Text()
            # Add expand/collapse indicator for parents with children
            if has_children:
                if task_id in self.expanded_parents:
                    label_text.append("▼ ", style=STYLES["dim"])
                else:
                    label_text.append("▶ ", style=STYLES["dim"])
            label_text.append(display_text if display_text else "")

        # Format second column (task ID or plan UUID depending on mode)
        id_display = plan_uuid if self.show_label_mode else task_id
        task_id_text = Text(id_display, style=STYLES["subtitle"])

        # Format timestamps (remove microseconds)
        started_text = started if started else ""
        ended_text = ended if ended else ""

        # Color-code state (full word)
        if state == "stopped":
            state_text = Text(state, style=STYLES["error_text"])
        elif state == "running":
            state_text = Text(state, style=STYLES["info_text"])
        elif state == "paused":
            state_text = Text(state, style=STYLES["warning_text"])
        else:
            state_text = Text(state if state else "")

        # Color-code result (full word)
        if result == "error":
            result_text = Text(result, style=STYLES["error_text"])
        elif result == "warning":
            result_text = Text(result, style=STYLES["warning_text"])
        elif result == "success":
            result_text = Text(result, style=STYLES["success_text"])
        else:
            result_text = Text(result if result else "")

        # Add row - match column order: Result, State, Label, ID, Started, Ended
        row_key = f"task_{task_id}"
        self.add_row(
            result_text,
            state_text,
            label_text,
            task_id_text,
            started_text,
            ended_text,
            key=row_key
        )

        # Store row key in ordered list
        self.row_keys.append(row_key)

        # Store plan UUID for navigation (for both parent and child tasks)
        # Every task has actions, so all should be navigable
        if plan_uuid:
            self.row_to_plan[row_key] = plan_uuid

        # Store task_id for parent tasks (for expand/collapse)
        if not is_child:
            if not hasattr(self, 'row_to_task_id'):
                self.row_to_task_id = {}
            self.row_to_task_id[row_key] = task_id

    def toggle_columns(self) -> None:
        """Toggle between Action/ID and Label/UUID display."""
        # Save current scroll position and cursor
        cursor_row = self.cursor_row

        # Toggle the mode
        self.show_label_mode = not self.show_label_mode

        # Clear and rebuild table to recalculate column widths
        self.clear(columns=True)
        self._add_columns()
        self._render_table()

        # Restore cursor position
        if cursor_row is not None and cursor_row < len(self.row_keys):
            self.move_cursor(row=cursor_row)

    def expand_task(self) -> None:
        """Expand current parent task to show children."""
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]

        # Only expand parent tasks
        if not hasattr(self, 'row_to_task_id') or row_key not in self.row_to_task_id:
            return

        task_id = self.row_to_task_id[row_key]

        # Check if this task has children
        if task_id not in self.children_by_parent:
            return

        # Save cursor position
        saved_cursor = self.cursor_row

        # Expand the parent
        self.expanded_parents.add(task_id)

        # Re-render table
        self._render_table()

        # Restore cursor position
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def collapse_task(self) -> None:
        """Collapse current parent task to hide children."""
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]

        # Only collapse parent tasks
        if not hasattr(self, 'row_to_task_id') or row_key not in self.row_to_task_id:
            return

        task_id = self.row_to_task_id[row_key]

        # Check if this task has children
        if task_id not in self.children_by_parent:
            return

        # Save cursor position
        saved_cursor = self.cursor_row

        # Collapse the parent
        self.expanded_parents.discard(task_id)

        # Re-render table
        self._render_table()

        # Restore cursor position
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)


class ActionsDataTable(DataTable):
    """DataTable widget for displaying actions for a specific plan."""

    def __init__(self, db, conf, plan_uuid=None, **kwargs):
        """Initialize actions data table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: Optional plan UUID to filter actions
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        """Load and display actions data when widget is mounted."""
        # Add columns - widths set to match content to minimize spacing
        self.add_column("Act", key="action_id", width=3)
        self.add_column("Action Class", key="action_class", width=55)
        self.add_column("R", key="result", width=1)
        self.add_column("Started", key="started", width=19)
        self.add_column("Ended", key="ended", width=19)
        self.add_column("Exec Time", key="exec_time", width=10)

        # Build query based on whether we're filtering by plan UUID
        if self.plan_uuid:
            actions_query = (
                "SELECT s.action_id, s.action_class, p.result, "
                "MIN(s.started_at), MAX(s.ended_at), "
                "SUM(s.execution_time) "
                "FROM dynflow_steps s "
                "LEFT JOIN dynflow_execution_plans p ON s.execution_plan_uuid = p.uuid "
                "WHERE s.execution_plan_uuid = ? "
                "GROUP BY s.action_id "
                "ORDER BY s.action_id"
            )
            rows = self.db.query(actions_query, (self.plan_uuid,))
        else:
            actions_query = (
                "SELECT s.action_id, s.action_class, p.result, "
                "MIN(s.started_at), MAX(s.ended_at), "
                "SUM(s.execution_time) "
                "FROM dynflow_steps s "
                "LEFT JOIN dynflow_execution_plans p ON s.execution_plan_uuid = p.uuid "
                "GROUP BY s.execution_plan_uuid, s.action_id "
                "ORDER BY MIN(s.started_at) DESC "
                "LIMIT 1000"
            )
            rows = self.db.query(actions_query)

        # Add rows with color coding
        for row in rows:
            action_id = str(row[0])[:3] if row[0] else ""
            action_class = str(row[1])[:55] if row[1] else ""
            result = str(row[2])[:12] if row[2] else ""
            started = str(row[3])[:19] if row[3] else ""
            ended = str(row[4])[:19] if row[4] else ""
            exec_time = f"{row[5]:.2f}s" if row[5] else "0.00s"

            # Skip successful if not showing all
            if not self.conf.args.showall and result == "success":
                continue

            # Color-code result (first letter only)
            result_letter = result[0].upper() if result else ""
            if result == "error":
                result_text = Text(result_letter, style=STYLES["error_text"])
            elif result == "warning":
                result_text = Text(result_letter, style=STYLES["warning_text"])
            elif result == "success":
                result_text = Text(result_letter, style=STYLES["success_text"])
            else:
                result_text = Text(result_letter)

            self.add_row(
                action_id,
                action_class,
                result_text,
                started,
                ended,
                exec_time,
                key=f"action_{action_id}"
            )


class ActionDetailsHeader(Static):
    """Display action details header (Task, Label, ID, Caller, Plan)."""

    def __init__(self, db, plan_uuid, **kwargs):
        """Initialize action details header.

        Args:
            db: OutputSQLite database instance
            plan_uuid: The execution plan UUID
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.plan_uuid = plan_uuid
        # Detect database type once
        self.is_postgres = hasattr(db, '_conn') and hasattr(
            db._conn, 'server_version'
        )

    def on_mount(self) -> None:
        """Load and display action details when mounted."""
        # Use the shared query to get actions for this plan
        from dynflowbrowser.lib.ui.shared import ActionQueries

        # Get task/plan info
        if self.is_postgres:
            task_result = self._get_task_info_postgres()
        else:
            task_result = self._get_task_info_sqlite()

        if task_result and len(task_result) > 0:
            row = task_result[0]
            label = str(row[0]) if row[0] else "N/A"
            task = str(row[1]) if row[1] else "N/A"
            task_id = str(row[2]) if row[2] else "N/A"
        else:
            label = "N/A"
            task = "N/A"
            task_id = "N/A"

        # Get caller_execution_plan_id from first action (index 11)
        actions = ActionQueries.get_actions_for_plan(self.db, self.plan_uuid)
        caller = None
        if actions and len(actions) > 0:
            caller_val = actions[0][11]  # caller_execution_plan_id at index 11
            if caller_val and str(caller_val).strip():
                caller = str(caller_val)

        # Build multi-line header with wrapping
        from rich.console import Console

        # Get terminal width
        console = Console()
        width = console.width if console.width else 80

        lines = []
        current_line = Text()

        # Add items with wrapping logic
        items = [
            ("Task: ", task),
            ("Label: ", label),
            ("Task ID: ", str(task_id)),
        ]

        if caller and caller.strip():
            items.append(("Caller Task ID: ", caller))

        items.append(("Plan UUID: ", self.plan_uuid))

        for i, (key, value) in enumerate(items):
            # Create the key-value pair
            pair = Text()
            pair.append(key, style=STYLES["key"])
            pair.append(value)

            # Check if adding this pair would exceed width
            test_line = current_line.copy()
            if len(test_line) > 0:
                test_line.append(" | ")
            test_line.append_text(pair)

            # If it fits, add it to current line
            if len(test_line) <= width:
                if len(current_line) > 0:
                    current_line.append(" | ")
                current_line.append_text(pair)
            else:
                # Save current line and start new one with this pair
                if len(current_line) > 0:
                    lines.append(current_line)
                current_line = pair.copy()

        # Add the last line
        if len(current_line) > 0:
            lines.append(current_line)

        # Combine all lines
        header = Text()
        for i, line in enumerate(lines):
            header.append_text(line)
            if i < len(lines) - 1:
                header.append("\n")

        self.update(header)

    def _get_task_info_postgres(self):
        """Get task/plan info from PostgreSQL."""
        task_query = """
            SELECT p.label, t.action, t.id
            FROM dynflow_execution_plans p
            LEFT JOIN foreman_tasks_tasks t
                ON p.uuid = t.external_id::uuid
            WHERE p.uuid = %s
            LIMIT 1
        """
        return self.db.query(task_query, (self.plan_uuid,))

    def _get_task_info_sqlite(self):
        """Get task/plan info from SQLite."""
        task_query = """
            SELECT p.label, t.action, t.id
            FROM dynflow_execution_plans p
            LEFT JOIN foreman_tasks_tasks t
                ON p.uuid = t.external_id
            WHERE p.uuid = ?
            LIMIT 1
        """
        return self.db.query(task_query, (self.plan_uuid,))


class ActionStatsPanel(Static):
    """Panel showing Top Dynflow and Pulp stats for a specific plan."""

    def __init__(self, db, conf, plan_uuid, **kwargs):
        """Initialize action stats panel.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: The execution plan UUID
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid

    def on_mount(self) -> None:
        """Load and display stats when mounted."""
        self.update_stats()

    def update_stats(self) -> None:
        """Update the stats display."""
        from rich.console import Group
        from dynflowbrowser.lib.util import Util

        util = Util('W')

        # Get top Dynflow steps for this plan using shared query
        dynflow_stats = StatsQueries.get_dynflow_plan_exectime(
            self.db,
            self.plan_uuid
        )

        # Create Rich table for Dynflow
        dynflow_table = Table(
            title=f"[{STYLES['bold']}]Top Dynflow[/]",
            show_header=True,
            header_style=STYLES["section_title"],
            expand=False,
            box=None
        )
        dynflow_table.add_column("Exectime", justify="right", no_wrap=True)
        dynflow_table.add_column("Steps", justify="right", no_wrap=True)
        dynflow_table.add_column("Label", style=STYLES["dim"], no_wrap=True, overflow="ellipsis")

        for row in dynflow_stats:
            exec_time = f"{float(row[0]):.0f}" if row[0] else "0"
            steps = str(row[1]) if row[1] else "0"
            label = str(row[2]) if row[2] else "N/A"
            dynflow_table.add_row(exec_time, steps, label)

        # Get Pulp data from action outputs using shared query
        pulp_stats = {}
        actions = StatsQueries.get_actions_with_pulp_for_plan(
            self.db,
            self.plan_uuid
        )

        for action in actions:
            output = action[0]
            pulp_tasks = FormatHelpers.parse_pulp_tasks(output)

            for task in pulp_tasks:
                # Skip tasks without finished_at (pending/running tasks)
                if 'finished_at' not in task or not task['finished_at']:
                    continue
                if 'pulp_created' not in task or not task['pulp_created']:
                    continue

                task_name = task.get('name', 'Unknown')
                finished = util.date_from_string(task['finished_at'])
                created = util.date_from_string(task['pulp_created'])
                exec_time = (finished - created).total_seconds()

                if task_name not in pulp_stats:
                    pulp_stats[task_name] = [0, 0]
                pulp_stats[task_name][0] += exec_time
                pulp_stats[task_name][1] += 1

        # Create Pulp table
        pulp_table = Table(
            title=f"[{STYLES['bold']}]Top Pulp[/]",
            show_header=True,
            header_style=STYLES["section_title"],
            expand=False,
            box=None
        )
        pulp_table.add_column("Exectime", justify="right", no_wrap=True)
        pulp_table.add_column("Count", justify="right", no_wrap=True)
        pulp_table.add_column("Name", style=STYLES["dim"], no_wrap=True, overflow="ellipsis")

        # Sort and show top 5 Pulp tasks
        if pulp_stats:
            sorted_pulp = sorted(
                pulp_stats.items(),
                key=lambda x: x[1][0],
                reverse=True
            )[:5]

            for task_name, (exec_time, count) in sorted_pulp:
                pulp_table.add_row(
                    f"{exec_time:.0f}",
                    str(count),
                    task_name
                )
        else:
            pulp_table.add_row("-", "-", "No Pulp data")

        # Combine both tables
        group = Group(dynflow_table, "", pulp_table)
        self.update(group)


class ActionsTreeTable(DataTable):
    """Tree-style table for displaying actions and their steps."""

    def __init__(self, db, conf, plan_uuid=None, **kwargs):
        """Initialize actions tree table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: Plan UUID to filter actions
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.show_cursor = True
        # Track expanded rows and details
        self.row_keys = []
        self.row_data = {}  # Store full row data for detail display
        self.expanded_actions = set()  # Track which actions are expanded
        self.action_steps = {}  # Map action_id to list of step keys
        self.step_rows = {}  # Map step key to row index
        # Dynamic width for time columns
        self.max_real_time_width = 4  # Minimum for "0.00"
        self.max_exec_time_width = 4

    def on_mount(self) -> None:
        """Load and display actions/steps when mounted."""
        # Columns - Status first, dates use 4-digit year format
        self.add_column("Status", key="status", width=None)
        self.add_column("Action / Step", key="action", width=None)
        self.add_column("Started At", key="started", width=19)
        self.add_column("Ended At", key="ended", width=19)
        self.add_column("RealT", key="real_time", width=None)
        self.add_column("ExecT", key="exec_time", width=None)

        # Fetch actions with steps
        self._load_actions()

    def _render_table(self) -> None:
        """Render all actions and expanded steps in hierarchical order."""
        # Clear current rows
        self.clear()
        self.row_keys.clear()
        self.row_data.clear()

        # Render root actions recursively
        for action in self.root_actions:
            self._render_action_tree(action, depth=0)

    def _calculate_time_widths(self) -> None:
        """Calculate maximum width needed for time columns."""
        # Scan all steps to find max width needed
        for action_id, steps in self.steps_by_action.items():
            for step in steps:
                # Format as it will appear
                real_time = f"{step[6]:.2f}" if step[6] else "0.00"
                exec_time = f"{step[7]:.2f}" if step[7] else "0.00"

                # Update max widths
                self.max_real_time_width = max(
                    self.max_real_time_width,
                    len(real_time)
                )
                self.max_exec_time_width = max(
                    self.max_exec_time_width,
                    len(exec_time)
                )

    def _load_actions(self) -> None:
        """Load actions and steps from database."""
        # Query all actions for this plan using shared query
        actions_raw = ActionQueries.get_actions_simple(
            self.db,
            self.plan_uuid
        )

        # Deduplicate actions by id (just in case)
        seen_ids = set()
        actions_deduped = []
        for action in actions_raw:
            action_id = action[0]
            if action_id not in seen_ids:
                seen_ids.add(action_id)
                actions_deduped.append(action)

        # Build action hierarchy using shared code
        self.root_actions, self.child_actions, self.actions_by_id = (
            ActionHierarchy.build_hierarchy(actions_deduped)
        )

        # Query steps for actions using shared query
        self.steps_by_action = ActionQueries.get_steps_by_action(
            self.db,
            self.plan_uuid
        )

        # Store which actions have steps
        for action_id in self.actions_by_id:
            if action_id in self.steps_by_action:
                self.action_steps[action_id] = self.steps_by_action[action_id]

        # Calculate optimal widths for time columns
        self._calculate_time_widths()

        # Auto-expand actions with non-success states
        # This includes actions where the action itself OR any descendant has issues
        self._auto_expand_non_success()

        # Render the table
        self._render_table()

    def _auto_expand_non_success(self):
        """Auto-expand actions that have non-success states.

        Simple approach:
        - If an action status is not "success": expand all parents up to root
        - If a step status is not "success": expand all parents up to root
        - Stop iterating when finding a parent that's already expanded
        """
        actions_to_expand = set()

        # Build parent map (reverse of child_actions)
        action_to_parent = {}
        for parent_id, children in self.child_actions.items():
            for child_action in children:
                child_id = child_action[0]
                action_to_parent[child_id] = parent_id

        def expand_all_parents(action_id):
            """Add action and all its parents to expansion set.

            Stops when finding a parent already in the expansion set.
            """
            current = action_id
            visited = set()
            while True:
                if current in visited:
                    break
                visited.add(current)

                # If already expanded, stop iterating
                if current in actions_to_expand:
                    break

                actions_to_expand.add(current)

                if current not in action_to_parent:
                    break
                current = action_to_parent[current]

        # 1. Find actions with non-success status
        for action_id, action in self.actions_by_id.items():
            # Action state is at index 10
            action_state = str(action[10]).lower() if action[10] else ""
            if action_state and action_state != "success":
                expand_all_parents(action_id)

        # 2. Find actions with steps that have non-success status
        for action_id, steps in self.steps_by_action.items():
            for step in steps:
                # Step state is at index 3
                step_state = str(step[3]).lower() if step[3] else ""
                if step_state and step_state != "success":
                    expand_all_parents(action_id)
                    break  # Only need one non-success step

        self.expanded_actions = actions_to_expand

    def _render_action_tree(self, action, depth=0) -> None:
        """Recursively render an action and its children/steps.

        Args:
            action: Action data tuple
            depth: Nesting depth (0 for root)
        """
        action_id = action[0]
        has_steps = action_id in self.action_steps
        has_children = action_id in self.child_actions

        # Add the action row
        self._add_action_row(action, has_steps=has_steps, has_children=has_children, depth=depth)

        # If expanded, add steps and child actions
        if action_id in self.expanded_actions:
            # Add steps first
            if has_steps:
                # Get run_step_id for step labeling
                run_step_id = action[3] if action[3] else action_id
                for step in self.action_steps[action_id]:
                    self._add_step_row(action_id, run_step_id, step, depth=depth)

            # Then add child actions recursively
            if has_children:
                for child_action in self.child_actions[action_id]:
                    self._render_action_tree(child_action, depth=depth + 1)

    def _add_action_row(self, action, has_steps=False, has_children=False, depth=0) -> None:
        """Add an action row.

        Args:
            action: Action data tuple
            has_steps: Whether this action has steps
            has_children: Whether this action has child actions
            depth: Nesting depth for indentation
        """
        action_id = action[0]
        action_class = str(action[4]) if action[4] else ""
        run_step_id = action[3]  # run_step_id is at index 3

        # Get aggregated step data for this action
        started, ended, real_time, exec_time, state = self._get_action_aggregated_data(action_id)

        # Calculate indentation
        indent = "  " * depth

        # Format action text with expand indicator and ID
        action_text = Text()
        action_text.append(indent)

        # Show expand/collapse indicator if action has steps or children
        if has_steps or has_children:
            if action_id in self.expanded_actions:
                action_text.append("▼ ", style=STYLES["dim"])  # Expanded
            else:
                action_text.append("▶ ", style=STYLES["dim"])  # Collapsed

        # Format run_step_id with alert indicator if action has output data
        output = action[7] if len(action) > 7 else ""
        action_text.append(f"{run_step_id}", style=STYLES["dim"])
        if output and output != "{}":
            action_text.append("!", style=STYLES["error_text"])
            action_text.append(" ")
        else:
            action_text.append(": ", style=STYLES["dim"])

        action_text.append(action_class)

        # Color-code status (full word)
        if state == "error":
            status_text = Text(state, style=STYLES["error_text"])
        elif state == "warning":
            status_text = Text(state, style=STYLES["warning_text"])
        elif state == "success":
            status_text = Text(state, style=STYLES["success_text"])
        else:
            status_text = Text(state if state else "")

        row_key = f"action_{action_id}"
        # Match column order: Status, Action/Step, Started, Ended, RealT, ExecT
        self.add_row(
            status_text,
            action_text,
            started,
            ended,
            real_time,
            exec_time,
            key=row_key
        )
        self.row_keys.append(row_key)
        self.row_data[row_key] = {
            'type': 'action',
            'data': action,
            'action_id': action_id,
            'has_steps': has_steps,
            'has_children': has_children
        }

    def _format_time_right(self, value, column='real'):
        """Format time value with right alignment.

        Args:
            value: Time value to format
            column: 'real' or 'exec' to determine which width to use

        Returns:
            Right-aligned string
        """
        width = (self.max_real_time_width if column == 'real'
                 else self.max_exec_time_width)
        return str(value).rjust(width)

    def _get_action_aggregated_data(self, action_id):
        """Get aggregated step data for an action.

        Args:
            action_id: The action ID

        Returns:
            Tuple of (started, ended, real_time, exec_time, state)
        """
        if action_id not in self.steps_by_action:
            return "", "", self._format_time_right("0.00", 'real'), self._format_time_right("0.00", 'exec'), ""

        steps = self.steps_by_action[action_id]

        # Aggregate data from steps
        started_times = [step[4] for step in steps if step[4]]
        ended_times = [step[5] for step in steps if step[5]]
        real_times = [step[6] for step in steps if step[6]]
        exec_times = [step[7] for step in steps if step[7]]
        states = [step[3] for step in steps if step[3]]

        started = format_date(min(started_times)) if started_times else ""
        ended = format_date(max(ended_times)) if ended_times else ""
        real_time = self._format_time_right(f"{sum(real_times):.2f}", 'real') if real_times else self._format_time_right("0.00", 'real')
        exec_time = self._format_time_right(f"{sum(exec_times):.2f}", 'exec') if exec_times else self._format_time_right("0.00", 'exec')

        # Get the "worst" state (error > warning > skipped > pending > success)
        state_priority = {'error': 0, 'warning': 1, 'skipped': 2, 'pending': 3, 'suspended': 4, 'success': 5}
        state = min(states, key=lambda s: state_priority.get(str(s).lower(), 999)) if states else ""

        return started, ended, real_time, exec_time, state

    def _add_step_row(self, action_id, run_step_id, step, depth=0) -> None:
        """Add a step row under an action.

        Args:
            action_id: Parent action ID (for row key)
            run_step_id: Run step ID to display (e.g., 29)
            step: Step data tuple
            depth: Nesting depth for indentation
        """
        step_id = step[1]
        action_class = str(step[10]) if step[10] else ""
        # Format timestamps to YY-MM-DD HH:MM:SS
        started = format_date(step[4])
        ended = format_date(step[5])
        real_time = self._format_time_right(f"{step[6]:.2f}", 'real') if step[6] else self._format_time_right("0.00", 'real')
        exec_time = self._format_time_right(f"{step[7]:.2f}", 'exec') if step[7] else self._format_time_right("0.00", 'exec')
        state = str(step[3]) if step[3] else ""

        # Calculate indentation (steps are one level deeper than their action)
        indent = "  " * depth

        # Format step text (indented)
        step_text = Text()
        step_text.append(indent)
        step_text.append("  └─ ", style=STYLES["dim"])
        step_text.append(f"{run_step_id}.{step_id}", style=STYLES["dim"])

        # Add alert indicator if step has error content
        error = step[13] if len(step) > 13 else ""
        if error:
            step_text.append("!", style=STYLES["error_text"])
            step_text.append(" ")
        else:
            step_text.append(": ", style=STYLES["dim"])

        step_text.append(action_class)

        # Color-code status (full word)
        if state == "error":
            status_text = Text(state, style=STYLES["error_text"])
        elif state == "warning":
            status_text = Text(state, style=STYLES["warning_text"])
        elif state == "success":
            status_text = Text(state, style=STYLES["success_text"])
        else:
            status_text = Text(state if state else "")

        row_key = f"step_{action_id}_{step_id}"
        # Match column order: Status, Action/Step, Started, Ended, RealT, ExecT
        self.add_row(
            status_text,
            step_text,
            started,
            ended,
            real_time,
            exec_time,
            key=row_key
        )
        self.row_keys.append(row_key)
        self.row_data[row_key] = {
            'type': 'step',
            'data': step
        }

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row cursor changes to update bindings.

        Args:
            event: Row highlighted event
        """
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            # No row selected
            if hasattr(self.screen, 'update_bindings'):
                self.screen.update_bindings(None)
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key in self.row_data:
            row_type = self.row_data[row_key]['type']
            # Update bindings in parent screen
            if hasattr(self.screen, 'update_bindings'):
                self.screen.update_bindings(row_type)

    def expand_action(self) -> None:
        """Expand current action to show steps and child actions."""
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]

        # Only expand actions, not steps
        if row_info['type'] != 'action':
            return

        # Must have steps or children to expand
        if not row_info.get('has_steps') and not row_info.get('has_children'):
            return

        action_id = row_info['action_id']

        # Save cursor position
        saved_cursor = self.cursor_row

        # Expand the action
        self.expanded_actions.add(action_id)

        # Re-render entire table to show changes
        self._render_table()

        # Restore cursor position using move_cursor
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def collapse_action(self) -> None:
        """Collapse current action to hide steps and child actions."""
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]

        # Only collapse actions, not steps
        if row_info['type'] != 'action':
            return

        # Must have steps or children to collapse
        if not row_info.get('has_steps') and not row_info.get('has_children'):
            return

        action_id = row_info['action_id']

        # Save cursor position
        saved_cursor = self.cursor_row

        # Collapse the action
        self.expanded_actions.discard(action_id)

        # Re-render entire table to show changes
        self._render_table()

        # Restore cursor position using move_cursor
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def toggle_detail(self, detail_type: str) -> None:
        """Toggle detail display for the current row.

        Args:
            detail_type: Type of detail to show (input/output/data/error)
        """
        if self.cursor_row is None or self.cursor_row < 0 or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]
        row_type = row_info['type']
        action_data = row_info['data']

        # Get the appropriate data field based on type
        if row_type == 'action':
            # Action data indices: 0=id, 1=uuid, 2=caller_id, 3=run_step, 4=class,
            # 5=data, 6=input, 7=output, 8=result, 9=label, 10=caller_plan_id
            if detail_type == 'input':
                content = action_data[6] if len(action_data) > 6 else ""
                title = "Action Input"
            elif detail_type == 'output':
                content = action_data[7] if len(action_data) > 7 else ""
                title = "Action Output"
            elif detail_type == 'data':
                content = action_data[5] if len(action_data) > 5 else ""
                title = "Action Data"
            else:
                self.app.notify(f"{detail_type} not available for actions", severity="warning")
                return
        elif row_type == 'step':
            # Step data indices from steps table
            # 0=uuid, 1=id, 2=action_id, 3=state, 4=started, 5=ended, 6=real_time,
            # 7=exec_time, 8=progress_done, 9=progress_weight, 10=action_class,
            # 11=execution_plan_id, 12=queue, 13=error, 14=children, 15=data
            if detail_type == 'error':
                content = action_data[13] if len(action_data) > 13 else ""
                title = "Step Error"
            elif detail_type == 'queue':
                content = action_data[12] if len(action_data) > 12 else ""
                title = "Step Queue"
            elif detail_type == 'children':
                content = action_data[14] if len(action_data) > 14 else ""
                title = "Step Children"
            elif detail_type == 'data':
                content = action_data[15] if len(action_data) > 15 else ""
                title = "Step Data"
            else:
                self.app.notify(f"{detail_type} not available for steps", severity="warning")
                return
        else:
            return

        # Format the content
        if not content or content == '{}' or content == '':
            formatted_content = f"[{STYLES['dim']}]No data[/]"
        else:
            # Try to pretty-print JSON
            import json
            try:
                parsed = json.loads(content)
                formatted_content = json.dumps(parsed, indent=2)
            except Exception as e:
                with open('/tmp/detail_debug.log', 'a') as f:
                    f.write(f"JSON parse failed: {e}\n")
                formatted_content = str(content)

        # Show in modal
        from .app import DetailModal
        self.app.push_screen(DetailModal(title, formatted_content))



class HttpAccessInfo(Static):
    """Widget displaying HTTP server access information."""

    def __init__(self, server, url_path="/", **kwargs):
        """Initialize HTTP access info widget.

        Args:
            server: HTTP server instance
            url_path: URL path to append to URLs
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.server = server
        self.url_path = url_path

    def render(self):
        """Render the HTTP access information."""
        from rich.text import Text

        output = Text()

        # Direct HTTP Access section
        output.append("Direct HTTP Access\n", style=STYLES["section_title"])
        direct_lines = self.server.get_direct_access_lines(self.url_path)
        for line in direct_lines:
            # Colorize interface names (e.g., "wlp9s0f0:", "tun0:")
            if ": http://" in line:
                parts = line.split(": http://", 1)
                output.append(parts[0] + ":", style=STYLES["highlight"])
                output.append(" http://" + parts[1] + "\n")
            else:
                output.append(f"{line}\n")

        # Single empty line between sections
        output.append("\n")

        # SSH Tunnel Access section
        output.append("SSH Tunnel Access\n", style=STYLES["section_title"])
        ssh_lines = self.server.get_ssh_tunnel_lines(self.url_path)
        for i, line in enumerate(ssh_lines):
            # Colorize step labels
            if line.startswith("1. Create SSH tunnel") or \
               line.startswith("2. Then open in browser"):
                output.append(line, style=STYLES["highlight"])
            else:
                output.append(line)

            # Add newline except for last line
            if i < len(ssh_lines) - 1:
                output.append("\n")

        return output


class DetailPanel(VerticalScroll):
    """Scrollable panel for displaying detailed information."""

    def __init__(self, **kwargs):
        """Initialize detail panel.

        Args:
            **kwargs: Additional keyword arguments for VerticalScroll
        """
        super().__init__(**kwargs)
        self.border_title = "Details"

    def display_json(self, json_data: str, title: str = "JSON Data") -> None:
        """Display formatted JSON data.

        Args:
            json_data: JSON string to display
            title: Title for the display
        """
        self.border_title = title

        try:
            # Parse and pretty-print JSON
            parsed = json.loads(json_data)
            formatted = json.dumps(parsed, indent=2)

            # Clear existing content and add new
            self.remove_children()
            self.mount(Static(formatted))

        except (json.JSONDecodeError, TypeError):
            # Display as plain text if not valid JSON
            self.remove_children()
            self.mount(Static(f"[{COLORS['highlight']}]{json_data}[/]"))

    def display_text(self, text: str, title: str = "Details") -> None:
        """Display plain text.

        Args:
            text: Text to display
            title: Title for the display
        """
        self.border_title = title
        self.remove_children()
        self.mount(Static(text))

    def clear(self) -> None:
        """Clear the detail panel."""
        self.border_title = "Details"
        self.remove_children()
        self.mount(Static(f"[{STYLES['dim']}]Select an item to view details[/]"))
