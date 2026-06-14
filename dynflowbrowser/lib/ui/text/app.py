"""Textual TUI application for browsing Dynflow data."""
from textual.app import App
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.screen import Screen
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Static

from .httpd_info import HttpdInfoScreen
from .loading import LoadingScreen
from .theme import COLORS, STYLES
from .welcome import WelcomeScreen
from .widgets import AppHeader
from .widgets import HeaderSeparator
from .widgets import HostDetailsHeader
from .widgets import StatsPanel
from .widgets import TasksDataTable


class TasksScreen(Screen):
    """Main screen showing tasks list."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "back_to_welcome", "Back", show=True),
        Binding("h", "show_httpd_modal", "HTTP Access", show=True,
                key_display="│ h"),
        Binding("s", "toggle_stats", "Show/Hide Stats", show=True),
        Binding("t", "toggle_columns", "View Foreman/Dynflow", show=True,
                key_display="│ t"),
        Binding("d", "app.toggle_dark", "Dark Mode", show=False),
    ]

    def __init__(self, db, conf, show_welcome=False):
        """Initialize tasks screen.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            show_welcome: If True, ESC goes to welcome screen
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.stats_visible = False
        self.show_welcome = show_welcome

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in the tasks table (Enter key).

        Args:
            event: The row selected event
        """
        self.action_view_actions()

    def on_key(self, event) -> None:
        """Handle key presses for navigation.

        Args:
            event: The key event
        """
        table = self.query_one(TasksDataTable)

        # Only Enter navigates to actions
        if event.key == "enter":
            if table.cursor_row is not None:
                self.action_view_actions()
                event.prevent_default()
                event.stop()
        # Left/Right now scroll horizontally (default DataTable behavior)

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield AppHeader()
        version = self.conf.sos.get('version', '0')
        yield HeaderSeparator(version)

        # Stats panel (initially hidden) - expands below separator
        yield StatsPanel(
            self.db, self.conf, id="stats_panel", classes="hidden"
        )

        yield HostDetailsHeader(self.conf.sos)

        # Tasks table
        yield TasksDataTable(
            self.db,
            self.conf,
            id="tasks_table"
        )

        yield Footer()

    def on_mount(self) -> None:
        """Focus the table when screen is mounted."""
        table = self.query_one(TasksDataTable)
        table.focus()

    def action_back_to_welcome(self) -> None:
        """Go back to welcome screen or quit."""
        if self.show_welcome:
            self.app.action_switch_mode("welcome")
        else:
            self.app.action_quit()

    def action_toggle_columns(self) -> None:
        """Toggle between Action/ID and Label/Plan UUID."""
        table = self.query_one(TasksDataTable)
        table.toggle_columns()

    def action_toggle_stats(self) -> None:
        """Toggle the stats panel visibility."""
        stats_panel = self.query_one("#stats_panel")
        if self.stats_visible:
            stats_panel.add_class("hidden")
            self.stats_visible = False
        else:
            stats_panel.remove_class("hidden")
            self.stats_visible = True

    def action_view_actions(self) -> None:
        """View actions for the selected task."""
        table = self.query_one(TasksDataTable)

        # Get the row key for the current cursor position
        if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
            return

        row_key = table.row_keys[table.cursor_row]

        # Only navigate if this is a parent task
        if row_key in table.row_to_plan:
            plan_uuid = table.row_to_plan[row_key]
            self.app.push_screen(
                ActionsScreen(self.db, self.conf, plan_uuid)
            )

    def action_show_httpd_modal(self) -> None:
        """Show HTTP server access modal."""
        self.app.push_screen(HttpdAccessModal(self.conf, plan_uuid=None))


class ActionsScreen(Screen):
    """Screen showing actions and steps for a specific task/plan."""

    # All bindings with visual separators
    BINDINGS = [
        Binding("q", "app.quit", "Quit", priority=True),
        Binding("escape", "app.pop_screen", "Back", show=True),
        Binding("h", "show_httpd_modal", "HTTP Access", show=True,
                key_display="│ h"),
        Binding("s", "toggle_stats", "Show/Hide Stats", show=True),
        Binding("d", "show_detail_menu", "Details", show=True,
                key_display="│ d"),
    ]

    def __init__(self, db, conf, plan_uuid):
        """Initialize actions screen.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: The execution plan UUID to show actions for
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.stats_visible = False
        self.detail_visible = None
        self.current_row_type = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield AppHeader()
        version = self.conf.sos.get('version', '0')
        yield HeaderSeparator(version)

        # Stats panel (initially hidden) - expands below separator
        from .widgets import ActionStatsPanel
        yield ActionStatsPanel(
            self.db,
            self.conf,
            self.plan_uuid,
            id="action_stats_panel",
            classes="hidden"
        )

        # Action details header (Task, Label, ID, Caller, Plan)
        from .widgets import ActionDetailsHeader
        yield ActionDetailsHeader(self.db, self.plan_uuid, id="action_details")

        # Actions tree view
        from .widgets import ActionsTreeTable
        yield ActionsTreeTable(
            self.db,
            self.conf,
            plan_uuid=self.plan_uuid,
            id="actions_tree"
        )

        yield Footer()

    def action_toggle_stats(self) -> None:
        """Toggle the stats panel visibility."""
        stats_panel = self.query_one("#action_stats_panel")
        if self.stats_visible:
            stats_panel.add_class("hidden")
            self.stats_visible = False
        else:
            stats_panel.remove_class("hidden")
            self.stats_visible = True

    def action_expand_action(self) -> None:
        """Expand current action to show steps."""
        table = self.query_one("#actions_tree")
        if hasattr(table, 'expand_action'):
            table.expand_action()

    def action_collapse_action(self) -> None:
        """Collapse current action to hide steps."""
        table = self.query_one("#actions_tree")
        if hasattr(table, 'collapse_action'):
            table.collapse_action()

    def action_show_detail_menu(self) -> None:
        """Show detail menu for current row."""
        table = self.query_one("#actions_tree")

        # Get current row info
        if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
            return

        row_key = table.row_keys[table.cursor_row]

        # Get row data to check for alerts
        row_data = table.row_data.get(row_key)
        if not row_data:
            return

        # Determine row type and available options
        if row_key.startswith('action_'):
            action_data = row_data['data']
            # Check output field (index 7) for alert
            output = action_data[7] if len(action_data) > 7 else ""
            has_output_alert = output and output != "{}"

            options = [
                ("Input", "input", False),
                ("Output", "output", has_output_alert),
                ("Data", "data", False),
            ]
            title = "Action Details"
        elif row_key.startswith('step_'):
            step_data = row_data['data']
            # Check error field (index 13) for alert
            error = step_data[13] if len(step_data) > 13 else ""
            has_error_alert = bool(error)

            options = [
                ("Error", "error", has_error_alert),
                ("Queue", "queue", False),
                ("Children", "children", False),
                ("Data", "data", False),
            ]
            title = "Step Details"
        else:
            return

        # Show detail menu modal
        self.app.push_screen(
            DetailMenuModal(title, options, table, row_key)
        )

    def on_mount(self) -> None:
        """Setup when screen is mounted."""
        table = self.query_one("#actions_tree")
        table.focus()

    def on_key(self, event) -> None:
        """Handle key presses.

        Args:
            event: The key event
        """
        table = self.query_one("#actions_tree")

        # Enter expands/collapses nodes
        if event.key == "enter":
            if table.cursor_row is None or table.cursor_row >= len(table.row_keys):
                return

            row_key = table.row_keys[table.cursor_row]
            if row_key not in table.row_data:
                return

            row_data = table.row_data[row_key]

            # Only expand/collapse actions (not steps)
            if row_data['type'] == 'action':
                action_id = row_data['action_id']
                # Toggle expansion
                if action_id in table.expanded_actions:
                    table.collapse_action()
                else:
                    table.expand_action()
                event.prevent_default()
                event.stop()
        # Left/Right now scroll horizontally (default DataTable behavior)

    def update_bindings(self, row_type: str = None) -> None:
        """Update current row type for validation.

        Args:
            row_type: 'action' or 'step' or None
        """
        self.current_row_type = row_type

    def action_show_httpd_modal(self) -> None:
        """Show HTTP server access modal."""
        self.app.push_screen(
            HttpdAccessModal(self.conf, plan_uuid=self.plan_uuid)
        )


class HttpdAccessModal(ModalScreen):
    """Modal to show HTTP server access info or start the server."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
    ]

    def __init__(self, conf, plan_uuid=None, **kwargs):
        """Initialize HTTP access modal.

        Args:
            conf: Configuration object
            plan_uuid: Optional plan UUID for actions screen
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.server_started = False

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from rich.text import Text
        from textual.containers import Container
        from textual.containers import VerticalScroll

        with Container(id="httpd_modal_container", classes="modal-container"):
            # Create title with X on the same line (right-aligned)
            title_text = Text()
            title_len = len("HTTP Server Access")
            # Modal width 82, minus 2 for thick borders, minus 2 for padding
            modal_width = 82 - 2 - 2
            padding = modal_width - title_len - 3 - 1  # -3 for "[X]", -1 for leading space
            if padding < 1:
                padding = 1

            title_text.append(" ")  # Leading space
            title_text.append("HTTP Server Access", style=f"bold {COLORS['brand_orange']}")
            title_text.append(" " * padding)
            title_text.append("[X]", style=f"bold {COLORS['brand_orange']}")

            title_widget = Static(title_text, id="httpd_modal_title", classes="modal-title")
            title_widget.can_focus = True
            yield title_widget

            yield VerticalScroll(id="httpd_modal_content", classes="modal-content")

    def on_mount(self) -> None:
        """Setup initial content when modal is mounted."""
        self._update_content()

    def _update_content(self) -> None:
        """Update modal content based on server state."""
        content_area = self.query_one("#httpd_modal_content")
        content_area.remove_children()

        # Check if server is running
        server_running = (
            hasattr(self.app, 'httpd_server')
            and self.app.httpd_server is not None
        )

        if server_running:
            # Server is running - show access information
            self._show_access_info(content_area)
        else:
            # Server is stopped - ask to start
            self._show_start_prompt(content_area)

    def _show_start_prompt(self, container) -> None:
        """Show prompt to start the server.

        Args:
            container: Container to add widgets to
        """
        from textual.containers import Center

        # Message
        message = Static(
            "The HTTP server is currently stopped.\n\n"
            "Would you like to start it?",
            id="httpd_prompt_message"
        )
        container.mount(message)

        # Buttons - create and compose before mounting
        start_btn = Button("Start Server", variant="success", id="start-btn")
        cancel_btn = Button("Cancel", variant="warning", id="cancel-btn")

        button_container = Horizontal(id="httpd_prompt_buttons", classes="button-group")
        button_container._add_children(start_btn, cancel_btn)

        container.mount(Center(button_container))

        # Set default focus on Start Server button after mounting
        self.call_after_refresh(lambda: start_btn.focus())

    def _show_access_info(self, container) -> None:
        """Show server access information.

        Args:
            container: Container to add widgets to
        """
        from dynflowbrowser.lib.ui.text.widgets import HttpAccessInfo

        if not hasattr(self.app, 'httpd_server') or not self.app.httpd_server:
            return

        # Build URL path based on plan_uuid
        url_path = f"/?plan_uuid={self.plan_uuid}" if self.plan_uuid else "/"

        # Mount shared HttpAccessInfo widget
        container.mount(HttpAccessInfo(self.app.httpd_server, url_path))

    def action_start_server(self) -> None:
        """Start the HTTP server."""
        from dynflowbrowser.lib.ui.httpd.output import HttpdOutput
        from dynflowbrowser.lib.ui.httpd.server import DynamicHttpServer
        import threading
        import time

        # Don't start if already running
        if hasattr(self.app, 'httpd_server') and self.app.httpd_server:
            self._update_content()
            return

        # Show starting message
        content_area = self.query_one("#httpd_modal_content")
        content_area.remove_children()
        content_area.mount(
            Static("[bold green]Starting HTTP Server...[/bold green]")
        )

        # Compute stats
        httpd_output = HttpdOutput(self.conf)
        pulp_stats, dynflow_stats = httpd_output.compute_execution_stats()
        httpd_output.copy_static_assets()

        # Create and start server
        self.app.httpd_server = DynamicHttpServer(
            self.conf,
            pulp_stats,
            dynflow_stats,
            quiet=True,
            data_provider=httpd_output.data_provider
        )

        def start_server():
            self.app.httpd_server.start()

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        self.server_started = True

        # Update content to show access info
        self._update_content()

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()

    def on_click(self, event) -> None:
        """Handle clicks on title close button.

        Args:
            event: Click event
        """
        # Check if click was on title (which contains [X])
        if event.widget.id == "httpd_modal_title":
            # Click on right side area to close
            if event.x >= 25:
                self.action_dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "start-btn":
            self.action_start_server()
        elif event.button.id == "cancel-btn":
            self.action_dismiss()

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.screen.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.screen.focus_next()


class DetailMenuModal(ModalScreen):
    """Modal screen to show detail menu options."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
        Binding("1", "select(0)", "1", show=False),
        Binding("2", "select(1)", "2", show=False),
        Binding("3", "select(2)", "3", show=False),
        Binding("4", "select(3)", "4", show=False),
    ]

    def __init__(
            self,
            title: str,
            options: list,
            table,
            row_key: str,
            **kwargs
    ):
        """Initialize detail menu modal.

        Args:
            title: Title for the modal
            options: List of (label, detail_type, has_alert) tuples
            table: Reference to the ActionsTreeTable
            row_key: The current row key
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.title_text = title
        self.options = options
        self.table = table
        self.row_key = row_key
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from rich.text import Text
        from textual.containers import Container
        with Container(id="menu_container", classes="modal-container"):
            # Create title with X on the same line (right-aligned)
            title_text = Text()
            # Calculate padding to push X to the right
            # Modal content width is less than container due to borders/padding
            title_len = len(self.title_text)
            # Modal width 40, minus 2 for thick borders, minus 2 for padding
            modal_width = 40 - 2 - 2
            padding = modal_width - title_len - 3 - 1  # -3 for "[X]", -1 for leading space
            if padding < 1:
                padding = 1

            title_text.append(" ")  # Leading space
            title_text.append(self.title_text, style=f"bold {COLORS['brand_orange']}")
            title_text.append(" " * padding)
            title_text.append("[X]", style=f"bold {COLORS['brand_orange']}")

            title_widget = Static(title_text, id="menu_title", classes="modal-title")
            title_widget.can_focus = True
            yield title_widget

            for idx, option_tuple in enumerate(self.options):
                label = option_tuple[0]
                has_alert = option_tuple[2] if len(option_tuple) > 2 else False

                # Build menu text with alert indicator
                menu_text = Text()
                menu_text.append(f"{idx + 1}. {label}")
                if has_alert:
                    menu_text.append(" !", style=STYLES["error_text"])

                style = "reverse" if idx == self.selected_index else ""
                menu_item = Static(
                    menu_text,
                    id=f"menu_item_{idx}",
                    classes=style
                )
                # Store index as a data attribute for click handling
                menu_item.data_index = idx
                yield menu_item

    def on_key(self, event) -> None:
        """Handle key presses for menu navigation."""
        if event.key == "up":
            self.selected_index = (self.selected_index - 1) % len(self.options)
            self.refresh_menu()
            event.prevent_default()
        elif event.key == "down":
            self.selected_index = (self.selected_index + 1) % len(self.options)
            self.refresh_menu()
            event.prevent_default()
        elif event.key == "enter":
            self.action_select(self.selected_index)
            event.prevent_default()

    def refresh_menu(self) -> None:
        """Refresh menu item styles based on selection."""
        from rich.text import Text
        for idx in range(len(self.options)):
            label = self.options[idx][0]
            has_alert = (
                self.options[idx][2] if len(self.options[idx]) > 2 else False
            )

            # Rebuild text with alert
            menu_text = Text()
            menu_text.append(f"{idx + 1}. {label}")
            if has_alert:
                menu_text.append(" !", style=STYLES["error_text"])

            item = self.query_one(f"#menu_item_{idx}")
            item.update(menu_text)

            if idx == self.selected_index:
                item.add_class("reverse")
            else:
                item.remove_class("reverse")

    def action_select(self, index: int) -> None:
        """Select a menu item and show its detail.

        Args:
            index: Index of selected option
        """
        if 0 <= index < len(self.options):
            detail_type = self.options[index][1]
            self.app.pop_screen()
            if hasattr(self.table, 'toggle_detail'):
                self.table.toggle_detail(detail_type)

    def on_click(self, event) -> None:
        """Handle clicks on menu items and close button.

        Args:
            event: Click event
        """
        # Check if click was on title (which contains [X])
        if event.widget.id == "menu_title":
            # Check if [X] position was clicked (right side)
            # Click anywhere on the right third of the title to close
            if event.x >= 25:  # Click on right side area
                self.action_dismiss()
        # Check if click was on a menu item
        elif hasattr(event.widget, 'data_index'):
            self.action_select(event.widget.data_index)

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()


class QuitModal(ModalScreen):
    """Modal screen for quit confirmation."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("left", "previous_button", "", show=False),
        Binding("right", "next_button", "", show=False),
        Binding("enter", "select", "Select", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose the quit confirmation modal."""
        from rich.text import Text
        from textual.containers import Container

        with Container(id="quit_container", classes="modal-container"):
            # Create title with X on the same line (right-aligned)
            title_text = Text()
            title_len = len("Quit DynflowBrowser?")
            # Modal width 50, minus 2 for thick borders, minus 2 for title padding (0 0 0 1 left + right margin)
            modal_width = 50 - 2 - 2
            padding = modal_width - title_len - 3 - 1  # -3 for "[X]", -1 for leading space
            if padding < 1:
                padding = 1

            title_text.append(" ")  # Leading space
            title_text.append("Quit DynflowBrowser?", style=f"bold {COLORS['brand_orange']}")
            title_text.append(" " * padding)
            title_text.append("[X]", style=f"bold {COLORS['brand_orange']}")

            title_widget = Static(title_text, id="quit_title", classes="modal-title")
            title_widget.can_focus = True
            yield title_widget

            with Container(id="quit_content", classes="modal-content"):
                with Horizontal(id="quit_buttons", classes="button-group"):
                    yield Button("Yes", id="quit_yes", variant="success")
                    yield Button("No", id="quit_no", variant="warning")

    def on_mount(self) -> None:
        """Focus the Yes button when modal opens."""
        self.query_one("#quit_yes", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "quit_yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel quit."""
        self.dismiss(False)

    def on_click(self, event) -> None:
        """Handle clicks on title close button.

        Args:
            event: Click event
        """
        # Check if click was on title (which contains [X])
        if event.widget.id == "quit_title":
            # Click on right side area to close (cancel quit)
            if event.x >= 25:
                self.action_cancel()

    def action_select(self) -> None:
        """Select focused button."""
        focused = self.focused
        if isinstance(focused, Button):
            focused.press()

    def action_previous_button(self) -> None:
        """Focus previous button."""
        self.focus_previous()

    def action_next_button(self) -> None:
        """Focus next button."""
        self.focus_next()


class AboutModal(ModalScreen):
    """Modal screen to display project information."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def __init__(self, version: str = "0", **kwargs):
        """Initialize about modal.

        Args:
            version: Project version
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.version = version

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from rich.text import Text
        from textual.containers import Container

        with Container(id="about_container", classes="modal-container"):
            # Create title with X on the same line (right-aligned)
            title_text = Text()
            title_len = len("About DynflowBrowser")
            # Modal width 70, minus 2 for thick borders, minus 2 for padding
            modal_width = 70 - 2 - 2
            padding = modal_width - title_len - 3 - 1  # -3 for "[X]", -1 for leading space
            if padding < 1:
                padding = 1

            title_text.append(" ")  # Leading space
            title_text.append("About DynflowBrowser", style=f"bold {COLORS['brand_orange']}")
            title_text.append(" " * padding)
            title_text.append("[X]", style=f"bold {COLORS['brand_orange']}")

            title_widget = Static(title_text, id="about_title", classes="modal-title")
            title_widget.can_focus = True
            yield title_widget

            content = (
                f"[bold {COLORS['accent']}]DynflowBrowser[/] "
                f"[{STYLES['dim']}]{self.version}[/]\n\n"
                f"[{STYLES['dim']}]Browse and analyze Dynflow execution data from "
                f"Red Hat Satellite sosreports.[/]\n\n"
                f"[{COLORS['accent']}]GitHub:[/] "
                "https://github.com/pafernanr/dynflowbrowser\n"
            )
            yield Static(content, id="about_content", classes="modal-content")

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.app.pop_screen()

    def on_click(self, event) -> None:
        """Handle clicks on title close button.

        Args:
            event: Click event
        """
        # Check if click was on title (which contains [X])
        if event.widget.id == "about_title":
            # Click on right side area to close
            if event.x >= 25:
                self.action_dismiss()


class DetailModal(ModalScreen):
    """Modal screen to display JSON detail data."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def __init__(self, title: str, content: str, **kwargs):
        """Initialize detail modal.

        Args:
            title: Title for the modal
            content: Content to display
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.title_text = title
        self.content_text = content

    def compose(self) -> ComposeResult:
        """Create modal widgets."""
        from rich.text import Text

        with VerticalScroll(id="detail_container", classes="modal-container"):
            # Title bar with close button - use Horizontal to properly align
            from textual.containers import Horizontal
            from rich.text import Text

            with Horizontal(id="detail_title_bar", classes="content-title"):
                title_text = Text()
                title_text.append(" ")  # Leading space
                title_text.append(self.title_text, style=f"bold {COLORS['brand_orange']}")

                close_text = Text()
                close_text.append("[X]", style=f"bold {COLORS['brand_orange']}")

                title_widget = Static(title_text, id="detail_title")
                title_widget.can_focus = False
                yield title_widget

                close_widget = Static(close_text, id="detail_close")
                close_widget.can_focus = True
                yield close_widget

            yield Static(self.content_text, id="detail_content", classes="modal-content")

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.dismiss()

    def on_click(self, event) -> None:
        """Handle clicks on title close button.

        Args:
            event: Click event
        """
        # Check if click was on close button
        if event.widget.id == "detail_close":
            self.action_dismiss()


class PostgresConnectionScreen(Screen):
    """PostgreSQL connection parameter input screen."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", priority=True),
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("enter", "connect", "Connect", show=True),
    ]

    CSS = """
    PostgresConnectionScreen {
        background: $surface;
    }

    #main-content {
        align: center middle;
        height: 1fr;
    }

    LogoBanner {
        width: 100%;
        margin: 0;
    }

    #postgres-title {
        width: 100%;
        margin: 1 0;
    }

    #postgres-form {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 0;
        margin: 0;
    }

    .postgres_row {
        width: 100%;
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }

    .postgres_label {
        width: 13;
    }

    .postgres_label_small {
        width: 11;
    }

    .postgres_field {
        width: 1fr;
        margin-right: 2;
    }

    .postgres_input_small {
        width: 10;
    }

    #postgres_task_days {
        width: 10;
    }

    #postgres-buttons {
        margin-top: 1;
    }

    #postgres-buttons Button {
        width: 20;
    }
    """

    def __init__(self, conf, **kwargs):
        """Initialize PostgreSQL connection screen.

        Args:
            conf: Configuration object
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.conf = conf

    def compose(self) -> ComposeResult:
        """Create screen widgets."""
        from textual.containers import Center
        from textual.containers import Horizontal
        from textual.containers import Middle
        from textual.containers import Vertical
        from textual.widgets import Button
        from textual.widgets import Footer
        from textual.widgets import Input
        from textual.widgets import Label
        from .widgets import LogoBanner

        with Middle(id="main-content"):
            with Vertical():
                yield LogoBanner()

                yield Static(
                    "PostgreSQL Direct Connection",
                    id="postgres-title",
                    classes="screen-title"
                )

                with Center():
                    with Vertical(id="postgres-form", classes="form-container"):
                        # Row 1: Server:port (1,1) and Database (1,2)
                        with Horizontal(classes="postgres_row"):
                            yield Label("Server:port", classes="postgres_label form-label")
                            yield Input(
                                value=self.conf.db_params.get('server', 'localhost:5432'),
                                placeholder="localhost:5432",
                                id="postgres_server",
                                classes="postgres_field"
                            )
                            yield Label("Database", classes="postgres_label form-label")
                            yield Input(
                                value=self.conf.db_params.get('database', 'foreman'),
                                placeholder="foreman",
                                id="postgres_database",
                                classes="postgres_field"
                            )

                        # Row 2: Username (2,1) and Password (2,2)
                        with Horizontal(classes="postgres_row"):
                            yield Label("Username", classes="postgres_label form-label")
                            yield Input(
                                value=self.conf.db_params.get('username', 'foreman'),
                                placeholder="foreman",
                                id="postgres_username",
                                classes="postgres_field"
                            )
                            yield Label("Password", classes="postgres_label form-label")
                            yield Input(
                                password=True,
                                placeholder="Enter password",
                                id="postgres_password",
                                classes="postgres_field"
                            )

                        # Row 3: Task Days (3,1)
                        with Horizontal(classes="postgres_row"):
                            yield Label("Task Days", classes="postgres_label form-label")
                            yield Input(
                                value=str(self.conf.args.task_days or 14),
                                placeholder="14",
                                id="postgres_task_days",
                                classes="postgres_input_small"
                            )

                    # Buttons - outside the form box
                    with Horizontal(id="postgres-buttons", classes="button-group"):
                        yield Button(
                            "Connect",
                            variant="primary",
                            id="btn_connect"
                        )
                        yield Button(
                            "Cancel",
                            variant="error",
                            id="btn_cancel"
                        )

        yield Footer()

    async def on_button_pressed(self, event) -> None:
        """Handle button press - async to await connect action."""
        if event.button.id == "btn_connect":
            await self.action_connect()
        else:
            self.action_cancel()

    async def on_input_submitted(self, event) -> None:
        """Handle ENTER key in any input field - trigger connect."""
        await self.action_connect()

    async def action_connect(self) -> None:
        """Handle connect action - async to await worker result."""
        from textual.widgets import Input

        # Get values from inputs
        self.conf.db_params['server'] = self.query_one(
            "#postgres_server", Input
        ).value
        self.conf.db_params['database'] = self.query_one(
            "#postgres_database", Input
        ).value
        self.conf.db_params['username'] = self.query_one(
            "#postgres_username", Input
        ).value
        self.conf.db_params['password'] = self.query_one(
            "#postgres_password", Input
        ).value

        # Update task_days
        try:
            task_days_str = self.query_one(
                "#postgres_task_days", Input
            ).value
            self.conf.args.task_days = int(task_days_str)
        except ValueError:
            pass

        # Show connecting screen with spinner (no progress bars)
        from rich.text import Text

        server = self.conf.db_params.get('server', 'localhost:5432')
        database = self.conf.db_params.get('database', 'foreman')
        username = self.conf.db_params.get('username', 'foreman')

        # Build message using theme colors (matching Welcome screen)
        message = Text()
        message.append("Connecting to: ", style=STYLES["key"])
        message.append(f"{username}@{server}/{database}", style=STYLES["value"])

        self.app.push_screen(
            LoadingScreen(
                message,
                show_progress=False
            )
        )

        # Run connection in worker thread and await result
        worker = self.app.run_worker(
            self.app._connect_postgres_worker,
            thread=True,
            exit_on_error=False
        )

        # Await the worker result
        result = await worker.wait()
        success, data = result

        # Handle result on main thread
        if success:
            self.app._setup_welcome_after_postgres(data)
        else:
            self.app._show_postgres_error(data)

    def action_cancel(self) -> None:
        """Handle cancel action - show quit confirmation."""
        self.app.action_request_quit()

    def action_request_quit(self) -> None:
        """Handle quit request."""
        self.app.action_request_quit()


class DynflowTUI(App):
    """Interactive Textual TUI for browsing Dynflow tasks and actions."""

    CSS = """
    /* ============================================
       GLOBAL REUSABLE CLASSES
       ============================================ */

    /* Modal/Dialog title bar - orange brand color */
    .modal-title {
        background: $boost;
        color: #EE7D42;
        padding: 0 0 0 1;
        text-style: bold;
    }

    /* Screen/Section title - cyan for emphasis */
    .screen-title {
        color: cyan;
        text-style: bold;
        text-align: center;
    }

    /* Content title - uses brand orange like modal titles */
    .content-title {
        background: $boost;
        color: #EE7D42;
        padding: 0 0 0 1;
        text-style: bold;
    }

    /* Modal container - standard modal wrapper */
    .modal-container {
        background: $surface;
        border: thick $primary;
        padding: 0;
    }

    /* Form container - for input forms */
    .form-container {
        border: solid $primary;
        padding: 0 1;
    }

    /* Form labels - yellow for consistency with httpd */
    .form-label {
        color: yellow;
        text-align: right;
        padding-right: 1;
        height: 1;
    }

    /* Form inputs with lighter background */
    .form-container Input {
        height: 1;
        border: none;
        background: $boost;
        padding: 0 1;
    }

    .form-container Input > .input--placeholder {
        color: $text-muted;
    }

    .form-container Input:focus {
        border: none;
        background: $panel;
    }

    .form-container Label {
        height: 1;
        content-align: right middle;
    }

    /* Button group container - centered buttons */
    .button-group {
        width: 100%;
        height: auto;
        align: center middle;
    }

    /* Standard button spacing */
    .button-group Button {
        margin: 0 1;
    }

    /* Modal/Dialog content area */
    .modal-content {
        padding: 1;
        height: auto;
    }

    /* Panel content with boost background */
    .panel-content {
        background: $boost;
        padding: 0 1;
    }

    /* ============================================
       SPECIFIC COMPONENT STYLES
       ============================================ */

    AppHeader {
        height: 1;
        dock: top;
        background: $boost;
        padding: 0 1;
        content-align: left middle;
    }

    HeaderSeparator {
        height: 1;
        padding: 0;
    }

    HostDetailsHeader {
        height: 2;
        background: $boost;
        padding: 0;
    }

    #action_details {
        height: auto;
        background: $panel;
        padding: 0;
    }

    #stats_panel, #action_stats_panel {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 0;
        background: $surface;
    }

    #stats_panel.hidden, #action_stats_panel.hidden {
        display: none;
    }

    #tasks_table, #actions_tree {
        height: 1fr;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--cursor {
        text-style: none;
    }

    DataTable > .datatable--hover {
        text-style: none;
    }

    .error {
        color: $error;
    }

    .success {
        color: $success;
    }

    .warning {
        color: $warning;
    }

    QuitModal {
        align: center middle;
    }

    #quit_container {
        width: 50;
        height: auto;
    }

    AboutModal {
        align: center middle;
    }

    #about_container {
        width: 70;
        height: auto;
    }

    #about_content {
        padding: 0;
    }

    HttpdAccessModal {
        align: center middle;
    }

    #httpd_modal_container {
        width: 82;
        height: auto;
    }

    #httpd_modal_content {
        max-height: 30;
    }

    #httpd_prompt_message {
        width: 100%;
        text-align: center;
        margin: 1 0;
    }

    #httpd_prompt_buttons Button {
        width: 20;
        height: 3;
    }

    DetailMenuModal {
        align: center middle;
    }

    #menu_container {
        width: 40;
        height: auto;
    }

    #menu_container Static {
        padding: 0 1;
        height: 1;
    }

    .reverse {
        background: $primary;
        color: $text;
    }

    DetailModal {
        align: center middle;
    }

    #detail_container {
        width: 90%;
        height: 90%;
    }

    #detail_title_bar {
        width: 100%;
        height: auto;
        background: $boost;
        padding: 0;
    }

    #detail_title {
        width: 1fr;
    }

    #detail_close {
        width: auto;
        dock: right;
    }

    #detail_content {
        padding: 0;
    }
    """

    MODES = {
        "welcome": WelcomeScreen,
        "tasks": TasksScreen,
        "httpd": HttpdInfoScreen,
    }

    def __init__(self, db, conf, show_welcome=False, initial_mode="welcome",
                 sqlite=None, postgres=None, input_dynflow=None):
        """Initialize the TUI application.

        Args:
            db: Database instance (OutputSQLite or InputPostgres)
            conf: Configuration object
            show_welcome: If True, show welcome screen first
            initial_mode: Initial mode to start with (welcome/tasks/httpd)
            sqlite: OutputSQLite instance for data import (SQLite mode)
            postgres: InputPostgres instance (PostgreSQL mode)
            input_dynflow: InputDynflow instance for reading CSV files (SQLite mode)
        """
        super().__init__()
        self.db = db
        self.conf = conf
        self.show_welcome = show_welcome
        self.initial_mode = initial_mode
        self.httpd_server = None
        self.sqlite = sqlite
        self.postgres = postgres
        self.input_dynflow = input_dynflow
        self.import_stats = None

    def on_mount(self) -> None:
        """Mount the initial screen."""
        # Install quit modal
        self.install_screen(QuitModal(), "quit")

        # PostgreSQL mode - check if we need to show connection modal
        if self.conf.args.dbserver:
            if self.postgres:
                # Already connected (console mode)
                self.db = self.postgres
                # Go directly to tasks screen
                if self.initial_mode == "welcome":
                    self.push_screen(WelcomeScreen(self.conf.sos))
                else:
                    self.push_screen(TasksScreen(self.db, self.conf))
            else:
                # TUI mode - show PostgreSQL connection screen
                self.push_screen(PostgresConnectionScreen(self.conf))
            return

        # SQLite mode - check if database exists and ask user before importing
        if self.conf.db_exists:
            # Show database reuse screen
            from .db_reuse import DatabaseReuseScreen
            self.push_screen(DatabaseReuseScreen(self.conf))
        # If we need to import data, show loading screen first
        elif self.conf.writesql and self.sqlite and self.input_dynflow:
            self._start_data_import()
        elif self.show_welcome:
            # Database was reused - count existing rows
            self._count_existing_data()
            # Show welcome screen with mode selection
            self.install_screen(WelcomeScreen(), "welcome")
            self.install_screen(
                TasksScreen(self.db, self.conf, show_welcome=True),
                "tasks"
            )
            self.push_screen("welcome")
            # Update welcome screen with stats
            if self.import_stats:
                self._update_welcome_stats()
        elif self.initial_mode == "httpd":
            # Start directly in httpd mode
            self._start_httpd_direct()
        else:
            # Go directly to tasks (no welcome to go back to)
            self.push_screen(
                TasksScreen(self.db, self.conf, show_welcome=False)
            )

    def _connect_postgres_worker(self):
        """Worker function to connect to PostgreSQL (runs in thread).

        ONLY creates the connection. The connection automatically fetches:
        - timezone (via SHOW timezone)
        - schema version (via SELECT version FROM dynflow_schema_info)

        Task UUIDs are loaded on-demand when needed.

        Returns:
            tuple: (success, data) where data is postgres instance or error
        """
        try:
            from dynflowbrowser.lib.inputpostgres import InputPostgres

            # Create PostgreSQL connection (blocking)
            # This automatically runs 2 queries in connect():
            #   1. SHOW timezone
            #   2. SELECT version FROM dynflow_schema_info
            postgres = InputPostgres(self.conf)

            return (True, postgres)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return (False, (str(e), tb))

    def _setup_welcome_after_postgres(self, postgres):
        """Setup welcome screen after successful PostgreSQL connection.

        Args:
            postgres: InputPostgres instance
        """
        # Pop loading screen
        self.pop_screen()

        # Set database
        self.db = postgres
        self.postgres = postgres

        # Install welcome screen
        welcome_screen = WelcomeScreen()
        self.install_screen(welcome_screen, "welcome")

        # Create tasks screen
        tasks_screen = TasksScreen(self.db, self.conf, show_welcome=True)
        self.install_screen(tasks_screen, "tasks")

        # Remove connection screen and show welcome
        self.pop_screen()
        self.push_screen("welcome")

        # Update welcome screen with connection details
        welcome_screen.update_postgres_connection_info(self.conf)

    def _show_postgres_error(self, error_data):
        """Show PostgreSQL connection error.

        Args:
            error_data: tuple of (error_message, traceback)
        """
        error_msg, tb = error_data

        # Pop loading screen
        self.pop_screen()

        # Show error modal
        error_text = (
            f"[bold red]Failed to connect to PostgreSQL[/bold red]\n\n"
            f"Error: {error_msg}\n\n"
            f"Traceback:\n{tb}\n\n"
            f"Press ESC to try again"
        )

        self.log.error(f"PostgreSQL connection error: {tb}")
        self.push_screen(DetailModal("Connection Error", error_text))

    def action_switch_mode(self, mode: str) -> None:
        """Switch to a different mode.

        Args:
            mode: Mode name (welcome/tasks/httpd)
        """
        if mode == "httpd":
            # Start HTTP server and show info screen
            self.start_httpd_server()
        elif mode in self.MODES:
            self.switch_screen(mode)
            # If switching to welcome, update server status
            if mode == "welcome":
                try:
                    welcome_screen = self.get_screen("welcome")
                    welcome_screen.update_httpd_button_status()
                except Exception:
                    pass

    def _start_httpd_direct(self) -> None:
        """Start httpd server directly (when launched with --httpd flag)."""
        # Create and push httpd info screen (can't go back)
        # Server will be started manually with (s) key
        server_info = {}
        httpd_screen = HttpdInfoScreen(
            self.conf, server_info, can_go_back=False
        )
        self.push_screen(httpd_screen)

    def start_httpd_server(self) -> None:
        """Start HTTP server and display info screen."""
        # Check if httpd screen is already installed
        if "httpd" in self._installed_screens:
            # Just switch to existing screen
            self.switch_screen("httpd")
            return

        # Create httpd info screen (can go back to welcome)
        # Server will be started manually with (s) key
        server_info = {}
        httpd_screen = HttpdInfoScreen(
            self.conf, server_info, can_go_back=True
        )
        self.install_screen(httpd_screen, "httpd")

        # Switch to httpd screen
        self.switch_screen("httpd")

    def _handle_db_reuse_decision(self, reuse: bool) -> None:
        """Handle the user's decision on database reuse.

        Args:
            reuse: True to reuse existing DB, False to overwrite
        """
        # Pop the db_reuse screen first
        self.pop_screen()

        if reuse:
            # Reuse existing database - skip import
            self.conf.writesql = False
            # Open database connection now
            if self.db is None:
                from dynflowbrowser.lib.outputsqlite import OutputSQLite
                self.db = OutputSQLite(self.conf)
            # Count existing data for stats
            self._count_existing_data()
            # Continue to welcome screen
            if self.show_welcome:
                from .welcome import WelcomeScreen
                self.install_screen(WelcomeScreen(), "welcome")
                self.install_screen(
                    TasksScreen(self.db, self.conf, show_welcome=True),
                    "tasks"
                )
                self.push_screen("welcome")
                # Update welcome screen with stats
                if self.import_stats:
                    self._update_welcome_stats()
            elif self.initial_mode == "httpd":
                self.push_screen("httpd")
            else:
                # Install and push tasks screen
                if not self.is_screen_installed("tasks"):
                    self.install_screen(
                        TasksScreen(self.db, self.conf, show_welcome=False),
                        "tasks"
                    )
                self.push_screen("tasks")
        else:
            # Overwrite - remove old database and import new data
            self.conf._remove_database_files()
            self.conf.writesql = True
            # Mark DB as no longer existing
            self.conf.db_exists = False
            # Save new execution arguments now that user confirmed
            self.conf._save_execution_args()
            # Start import
            if self.sqlite and self.input_dynflow:
                self._start_data_import()

    def _show_error_modal(self, message: str) -> None:
        """Show error message in a modal dialog.

        Args:
            message: Error message to display
        """
        from .app import DetailModal
        self.push_screen(DetailModal("Error", message))

    def _start_data_import(self) -> None:
        """Start the data import process with loading screen."""
        # Save execution args before starting import
        self.conf._save_execution_args()

        from .loading import LoadingScreen
        loading_screen = LoadingScreen()
        self.install_screen(loading_screen, "loading")
        self.push_screen("loading")
        # Start import in background worker
        self.run_worker(
            self._import_data_worker,
            name="import_data",
            exclusive=True,
            exit_on_error=False,
            thread=True
        )

    def _import_data_worker(self) -> None:
        """Import CSV data into SQLite with progress updates (runs in worker thread).

        Uses ThreadPoolExecutor to read and write all 4 table types in parallel.
        Each thread gets its own SQLite connection via write_threaded().
        """
        import time
        from concurrent.futures import ThreadPoolExecutor
        from dynflowbrowser.lib.outputsqlite import OutputSQLite

        stats = {}

        try:
            def error_callback(msg):
                self.call_from_thread(self._show_error_modal, msg)

            sqlite_worker = OutputSQLite(self.conf, error_callback)

            self.call_from_thread(
                self._update_loading_status,
                "Importing data (parallel)..."
            )

            def _import_table(dtype):
                dynflow = self.input_dynflow.read_dynflow(dtype)

                def progress_callback(current, total, _dtype=dtype):
                    self.call_from_thread(
                        self._update_loading_progress,
                        _dtype, current, total
                    )

                return sqlite_worker.write_threaded(
                    dtype, dynflow, progress_callback
                )

            workers = getattr(self.conf.args, 'workers', 4)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    dtype: pool.submit(_import_table, dtype)
                    for dtype in ['tasks', 'plans', 'actions', 'steps']
                }
                for dtype, future in futures.items():
                    stats[dtype] = future.result()

            # Create indexes (sequential, single connection)
            self.call_from_thread(
                self._update_loading_status,
                "Creating database indexes..."
            )
            self.call_from_thread(
                self._update_loading_progress,
                "indexes", 0, 100
            )
            sqlite_worker.create_indexes()
            self.call_from_thread(
                self._update_loading_progress,
                "indexes", 100, 100
            )

            sqlite_worker.close()

            time.sleep(0.5)

            self.import_stats = stats
            self.call_from_thread(self._switch_to_welcome)

        except Exception as e:
            import traceback
            error_msg = f"Import Error:\n{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.call_from_thread(self._show_error_modal, error_msg)
            self.call_from_thread(
                self._update_loading_status,
                "[bold red]Import failed - see error modal[/bold red]"
            )
            time.sleep(3600)

    def _switch_to_welcome(self) -> None:
        """Switch to welcome screen after import completes."""
        # Open database connection after import
        if self.db is None:
            from dynflowbrowser.lib.outputsqlite import OutputSQLite
            self.db = OutputSQLite(self.conf)

        # Switch to welcome screen
        self.install_screen(WelcomeScreen(), "welcome")
        self.install_screen(
            TasksScreen(self.db, self.conf, show_welcome=True),
            "tasks"
        )
        self.switch_screen("welcome")

        # Update welcome screen with stats
        if self.import_stats:
            self._update_welcome_stats()

    def _update_loading_status(self, message: str) -> None:
        """Update loading screen status message.

        Args:
            message: Status message to display
        """
        try:
            loading_screen = self.get_screen("loading")
            loading_screen.update_status(message)
        except Exception:
            pass

    def _update_loading_progress(self, dtype: str, current: int, total: int) -> None:
        """Update loading screen progress bar.

        Args:
            dtype: Data type (tasks, plans, actions, steps, indexes)
            current: Current progress
            total: Total items
        """
        try:
            loading_screen = self.get_screen("loading")
            loading_screen.update_progress(dtype, current, total)
        except Exception:
            pass

    def _update_welcome_stats(self) -> None:
        """Update welcome screen with import statistics."""
        try:
            welcome_screen = self.get_screen("welcome")
            welcome_screen.update_import_stats(self.import_stats)
            # Also update execution arguments
            welcome_screen.update_exec_args(self.conf.argsfile)
        except Exception:
            pass

    def _count_existing_data(self) -> None:
        """Count rows in existing database when reused."""
        try:
            stats = {}
            for dtype in ['tasks', 'plans', 'actions', 'steps']:
                count = self.db.query(f"SELECT COUNT(*) FROM {dtype}")[0][0]
                stats[dtype] = {
                    'dtype': dtype,
                    'rows': count,
                    'seconds': 0,
                    'speed': 0
                }
            self.import_stats = stats
        except Exception:
            pass

    def action_request_quit(self) -> None:
        """Show quit confirmation and exit if confirmed."""
        def check_quit(quit_confirmed: bool) -> None:
            """Exit if user confirmed quit."""
            if quit_confirmed:
                self.exit()

        self.push_screen(QuitModal(), check_quit)

    def action_quit(self) -> None:
        """Override default quit to show confirmation."""
        self.action_request_quit()
