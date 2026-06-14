import argparse
import os
import sys

from dynflowbrowser.lib.util import Util


def get_version():
    """Get version string from __VERSION__ file.

    Returns:
        str: Version string (e.g., 'v0.0.1rc6')
    """
    fname = os.path.join(os.path.dirname(__file__), '..', '__VERSION__')
    try:
        with open(fname, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


class Conf:

    def __init__(self, tui_mode=False):
        """Initialize configuration.

        Args:
            tui_mode: If True, skip console prompts for TUI handling
        """
        self.tui_mode = tui_mode
        self.cwd = os.getcwd()
        self.util = Util("W")
        self.dynflowdata = {
            'version': "0",
            'plans': {'times': 0},
            'steps': {'times': 0},
            'actions': {'times': 0},
            'includedUUID': [],
            }
        self.pulpcoredata = {
            'version': "0",
            'core_task': {'times': 0},
            'core_taskgroup': {'times': 0},
            'core_progressreport': {'times': 0},
            'core_groupprogressreport': {'times': 0}
            }
        self.writesql = True
        self.sos = {}
        self.dbfile = ""

        self.parser = argparse.ArgumentParser(
            description="Get sosreport dynflow files and generates user"
            + " friendly html pages for tasks, plans, actions and steps",
            epilog="""
Examples:
  # Combine state, result and time filters
  %(prog)s --state stopped --result error --task-days 10

  # Complex search query (AND / OR operators)
  %(prog)s --search="result != success" --task-days 3
  %(prog)s --search="label ~ Sync AND state = stopped AND result = error"
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
            )
        self.parser.add_argument(
            '-v',
            '--version',
            action='version',
            version=self.get_version(),
            )
        self.parser.add_argument(
            '--search',
            dest='search',
            help='Search query using foreman-rake syntax. '
                 'Supports operators: =, !=, ~, !~, >, <, >=, <= '
                 'and connectors: AND, OR',
            default=None
            )
        self.parser.add_argument(
            '--state',
            dest='state',
            help='Filter by task state. '
                 'Valid: paused, pending, planned, planning, running, stopped',
            choices=['paused', 'pending', 'planned',
                     'planning', 'running', 'stopped'],
            default=None
            )
        self.parser.add_argument(
            '--result',
            dest='result',
            help='Filter by task result. '
                 'Valid: error, pending, success, warning',
            choices=['error', 'pending', 'success', 'warning'],
            default=None
            )
        self.parser.add_argument(
            '--task-days',
            dest='task_days',
            help='Import only tasks from last N days. '
                 'Same as foreman-rake TASK_DAYS parameter.',
            type=int,
            default=None
            )
        self.parser.add_argument(
            '--dbserver',
            dest='dbserver',
            action='store_true',
            help='Connect directly to PostgreSQL instead of importing CSV to SQLite. '
                 'Requires PostgreSQL connection details.',
            default=False
            )
        self.parser.add_argument(
            '-w',
            '--workers',
            help="Number of worker threads for parallel CSV import. "
                 "Default is min(4, CPU count).",
            default=min(4, os.cpu_count() or 1),
            type=int
            )
        self.parser.add_argument(
            '-o',
            '--output_path',
            help="Write output to this path. Default is './dynflowbrowser/'.",
            default=self.cwd,
            type=self.valid_output_path
            )
        self.parser.add_argument(
            'sosreport_path',
            help='Path to sos report folder. Default is current path.',
            nargs='?'
            )
        self.args = self.parser.parse_args()

        # Auto-set task_days to 14 for PostgreSQL mode if not specified
        if self.args.dbserver and self.args.task_days is None:
            self.args.task_days = 14

        # Validate sosreport_path after parsing
        if self.args.sosreport_path is None:
            self.args.sosreport_path = self.cwd
        else:
            # Validate the provided path
            validated_path = self.valid_sosreport_path(
                self.args.sosreport_path
            )
            self.args.sosreport_path = validated_path

        # Backward compatibility: showall is True when no filters are specified
        self.args.showall = (
            self.args.search is None and
            self.args.state is None and
            self.args.result is None and
            self.args.task_days is None
        )

        # PostgreSQL connection setup
        if self.args.dbserver:
            self._setup_postgres_connection()
            # Set PostgreSQL-specific sos details (sets self.sos['sosname'])
            self._set_postgres_sos_details()
            # Use same output path pattern as sosreport mode
            self.args.output_path = (
                f"{self.args.output_path}/dynflowbrowser/{self.sos['sosname']}"
                .replace('//', '/')
            )
        else:
            # Validate sosreport path exists
            if not os.path.exists(self.args.sosreport_path):
                print(f"ERROR: sosreport path does not exist: {self.args.sosreport_path}")
                sys.exit(1)

            # Check for required files
            required_files = [
                'sos_commands/systemd/timedatectl',
                'hostname',
                'sos_commands/foreman/dynflow_schema_info'
            ]
            for required_file in required_files:
                file_path = os.path.join(self.args.sosreport_path, required_file)
                if not os.path.exists(file_path):
                    print(f"ERROR: Required file not found: {file_path}")
                    print(f"The path '{self.args.sosreport_path}' does not appear to be a valid sosreport directory.")
                    sys.exit(1)

            self.set_sos_details()
            self.args.output_path = (
                f"{self.args.output_path}/dynflowbrowser/{self.sos['sosname']}"
                .replace('//', '/')
            )

        # Create base output directory
        os.makedirs(self.args.output_path, exist_ok=True)

        # Database files only needed for SQLite mode
        if not self.args.dbserver:
            self.dbfile = self.args.output_path + "/dynflowbrowser.db"
            self.argsfile = self.args.output_path + "/execution_args.txt"

            # Check if database file already exists
            # Store DB existence info for TUI mode to handle
            self.db_exists = os.path.exists(self.dbfile) and self.writesql
        else:
            # PostgreSQL mode - no local database files
            self.dbfile = None
            self.argsfile = None
            self.dbfile = None
            self.argsfile = None
            self.db_exists = False

        # In non-TUI mode, ask user via console (legacy behavior)
        if self.db_exists and not self.tui_mode:
            # Show relative path for cleaner output
            rel_path = os.path.relpath(self.dbfile, self.cwd)
            print(f"\nDatabase file already exists: {rel_path}")
            prompt = "Reuse existing database? [y/N]: "
            response = input(prompt).strip().lower()
            if response == 'y':
                # Reuse existing database, skip data import
                self.writesql = False
                print("Reusing existing database...")
            else:
                # Overwrite - remove old database files
                self._remove_database_files()
                print("Overwriting database...")

        # In TUI mode, args are saved just before DB creation
        # In non-TUI mode (CLI), save args now
        if self.writesql and not self.tui_mode:
            self._save_execution_args()

    def _remove_database_files(self):
        """Remove database and related files."""
        # Remove database file
        if os.path.exists(self.dbfile):
            os.remove(self.dbfile)

        # Also remove WAL files if they exist
        for suffix in ['-wal', '-shm']:
            wal_file = self.dbfile + suffix
            if os.path.exists(wal_file):
                os.remove(wal_file)

        # Also remove args file when overwriting
        if os.path.exists(self.argsfile):
            os.remove(self.argsfile)

    def _save_execution_args(self):
        """Save execution arguments to a file."""
        try:
            with open(self.argsfile, 'w', encoding='utf-8') as f:
                f.write("Execution Arguments:\n")
                f.write("===================\n\n")

                # Build filter description
                filters = []
                if self.args.search:
                    filters.append(f"Search: {self.args.search}")
                if self.args.state:
                    filters.append(f"State: {self.args.state}")
                if self.args.result:
                    filters.append(f"Result: {self.args.result}")
                if self.args.task_days:
                    filters.append(f"Task Days: {self.args.task_days}")

                if filters:
                    f.write("Filters:\n")
                    for filter_item in filters:
                        f.write(f"  - {filter_item}\n")
                else:
                    f.write("Filters: None (showing all tasks)\n")

                f.write(f"\nOutput Path: {self.args.output_path}\n")
                f.write(f"SOS Report: {self.args.sosreport_path}\n")
        except Exception:
            pass  # Silently ignore errors saving args file

    def get_version(self):
        """Get version and store in sos dict.

        Returns:
            str: Version string
        """
        version = get_version()
        self.sos['version'] = version
        return version

    def valid_output_path(self, path):
        if path[:1] == "/":
            fullpath = path
        else:
            fullpath = f"{self.cwd}/{path}"
        if os.path.exists(fullpath):
            return fullpath
        else:
            raise argparse.ArgumentTypeError(
                f"{fullpath!r} is not a valid path.")

    def valid_sosreport_path(self, path):
        # If it's current directory (default), just return it
        if path == self.cwd or path == '.':
            return path
        p = path + "/sos_commands/foreman/dynflow_schema_info"
        if os.path.exists(p):
            return path
        else:
            raise argparse.ArgumentTypeError(
                f"{p!r} doesn't exist.")

    def _set_postgres_sos_details(self):
        """Set sos details from PostgreSQL connection instead of sosreport."""
        # Connection details for display
        server = self.db_params.get('server', 'localhost:5432')
        database = self.db_params.get('database', 'foreman')
        username = self.db_params.get('username', 'foreman')

        # Build display string for hostname (use server)
        self.sos['hostname'] = f"{server} (PostgreSQL)"

        # Timezone will be fetched from PostgreSQL server later by InputPostgres
        # For now, use a placeholder
        self.sos['timezone'] = 'UTC'  # Will be updated by InputPostgres

        # Use current time as localtime
        import datetime as dt
        self.sos['localtime'] = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Set database info instead of satellite version
        self.sos['satversion'] = f"PostgreSQL Direct Connection"

        # RAM/CPU not available - use N/A
        self.sos['ram'] = 'N/A (remote database)'
        self.sos['cpu'] = 'N/A (remote database)'

        # Tuning not available
        self.sos['tuning'] = 'N/A'

        # Version will be fetched from database
        self.dynflowdata['version'] = 'Unknown'  # Will be updated later

        # Set sosname for output directory (using database@server)
        self.sos['sosname'] = f"{database}@{server.split(':')[0]}"

    def parse_ram_info(self, free_output):
        """Parse free command output and return memory/swap in GB."""
        try:
            lines = free_output.strip().split('\n')
            mem_total = 0
            swap_total = 0

            for line in lines:
                if line.startswith('Mem:'):
                    # Extract total memory (second column)
                    parts = line.split()
                    mem_total = int(parts[1])
                elif line.startswith('Swap:'):
                    # Extract total swap (second column)
                    parts = line.split()
                    swap_total = int(parts[1])

            # Convert to GB (assuming input is in KB)
            mem_gb = round(mem_total / 1024 / 1024, 1)
            swap_gb = round(swap_total / 1024 / 1024, 1)

            return f"Physical: {mem_gb}G / Swap: {swap_gb}G"
        except Exception:
            # If parsing fails, return a simple message
            return "N/A"

    def set_sos_details(self):
        self.sos['timezone'] = self.util.exec_command(
            f"grep 'Time zone:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $3}'").strip()
        self.sos['localtime'] = self.util.exec_command(
            f"grep 'Local time:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $4\" 23:59:59\"}'").strip()
        self.sos['hostname'] = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/hostname").strip()
        ram_raw = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/free")
        self.sos['ram'] = self.parse_ram_info(ram_raw)
        self.sos['cpu'] = self.util.exec_command(
            f"grep -e '^CPU(s)'  {self.args.sosreport_path}/sos_commands/processor/lscpu "  # noqa E501
            + " | awk '{print $2}'").strip()
        self.sos['tuning'] = self.util.exec_command(
            f"grep tuning  {self.args.sosreport_path}/etc/foreman-installer/scenarios.d/satellite.yaml | cut -d ':' -f2")  # noqa E501
        self.sos['satversion'] = self.util.exec_command(
            f"grep -E 'satellite-6' {self.args.sosreport_path}/installed-rpms | cut -d ' ' -f1").strip()  # noqa E501
        self.dynflowdata['version'] = self.util.exec_command(
            f"tail -n3 {self.args.sosreport_path}/sos_commands/foreman/dynflow_schema_info | head -1 | sed 's/ *//'").strip()  # noqa E501
        self.sos['sosname'] = os.path.basename(
            os.path.normpath(self.args.sosreport_path))
        if self.sos['sosname'] == ".":
            self.sos['sosname'] = ""

    def get_satellite_db_password(self):
        """Extract db_password from satellite-answers.yaml.

        Returns:
            str: Database password or None if not found
        """
        yaml_path = "/etc/foreman-installer/scenarios.d/satellite-answers.yaml"

        if not os.path.exists(yaml_path):
            return None

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Match only lines starting with db_password: (after stripping)
                    # This excludes candlepin_db_password, pulpcore_db_password, etc.
                    stripped = line.strip()
                    if stripped.startswith('db_password:'):
                        # Extract password after the colon
                        password = stripped.split('db_password:', 1)[1].strip()
                        return password
        except Exception as e:
            self.util.debug("W", f"Could not read satellite-answers.yaml: {e}")
            return None

        return None

    def _setup_postgres_connection(self):
        """Prompt for PostgreSQL connection details."""
        import getpass

        self.db_params = {}

        # In TUI mode, skip prompts - will be handled by modal dialog
        # Set defaults that will be used
        if self.tui_mode:
            self.db_params = {
                'server': 'localhost:5432',
                'database': 'foreman',
                'username': 'foreman',
                'password': ''  # Will be set by modal
            }
            return

        # Console mode - prompt for connection details
        print("\nPostgreSQL Connection Settings:")
        print("=" * 40)

        # Server and port
        self.db_params['server'] = input("Server:port [localhost:5432]: ").strip() or "localhost:5432"

        # Database name
        self.db_params['database'] = input("Database name [foreman]: ").strip() or "foreman"

        # Username
        self.db_params['username'] = input("Username [foreman]: ").strip() or "foreman"

        # Password
        default_password = self.get_satellite_db_password()
        if default_password:
            use_default = input("Use password from satellite-answers.yaml? [Y/n]: ").strip().lower()
            if use_default != 'n':
                self.db_params['password'] = default_password
                print("Using password from satellite-answers.yaml")
            else:
                self.db_params['password'] = getpass.getpass("Password: ")
        else:
            self.db_params['password'] = getpass.getpass("Password: ")

        # Task days - ALWAYS show and allow editing
        current_task_days = self.args.task_days if self.args.task_days else "all"
        task_days_input = input(f"\nTask days [{current_task_days}]: ").strip()

        if task_days_input:
            try:
                self.args.task_days = int(task_days_input)
            except ValueError:
                print(f"Invalid number - keeping current value: {current_task_days}")

        if self.args.task_days:
            print(f"Will fetch tasks from last {self.args.task_days} days")
        else:
            print("Will fetch all tasks (no date filter)")

        print()
