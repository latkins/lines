from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Union

from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint
from rich.table import Table
from textual.app import App
from textual.widget import Widget
from textual.widgets import Footer, ScrollView

from lines.log import get_logger
from lines.process_traces import File, load_traces


def fmt_time(time_us: Union[int, float]) -> str:
    if time_us / 1000_000 > 1:
        # Show in s
        return f"{time_us / 1000_000:.2f}s"
    elif (time_us / 1000) > 1:
        return f"{time_us / 1000:.2f}ms"
        # Show in ms
    else:
        return f"{time_us}us"


"""
class FileList(Widget):
    def __init__(
        self,
    ):
        pass

    def render(self) -> Panel:
        pass
"""


class Viewer:
    def __init__(self, files_dict: Dict[Path, File]):
        self.files_dict = files_dict

    def view_file(self, file_name: str) -> List[str]:
        file = self.files_dict[Path(file_name)]
        with Path(file_name).open("r") as f:
            file_lines = [line.rstrip() for line in f.readlines()]

        max_line_len = min(77, max(map(len, file_lines)))

        marked_up_lines = []
        for line_no, code_line in enumerate(file_lines):
            code_line = file_lines[line_no][:max_line_len]
            info = ""

            scopes = file.scope[line_no]
            line_stats = file.line[line_no]
            if scopes and line_stats:
                scope = min(scopes, key=lambda i: i.length())

                scope_stats = scope.data.stats
                if scope_stats.calls > 0:
                    gpu_time = fmt_time(line_stats.device_total)
                    gpu_p = (
                        line_stats.device_total / scope_stats.device_total
                        if scope_stats.device_total
                        else 0
                    )
                    cpu_time = fmt_time(line_stats.host_total)
                    cpu_p = (
                        line_stats.host_total / scope_stats.host_total
                        if scope_stats.host_total
                        else 0
                    )
                    avg_tc = line_stats.tc_total_ratio
                    gpu_cell = f"{gpu_time} ({gpu_p:3.0%})"
                    cpu_cell = f"{cpu_time} ({cpu_p:3.0%})"
                    tc_cell = f"{avg_tc:3.0f}%"
                    info = f"{cpu_cell} {gpu_cell} {tc_cell}"

            marked_up_lines.append(f"{code_line:<{max_line_len}} | {info}")

            """
            if scope.data.stats.calls == 0:
                for i in range(scope.begin, scope.end):
                    # file_lines[i] = f"[grey]{file_lines[i]}[/grey]"
                continue
            file_lines[scope.begin - 1] = f"[red]{file_lines[scope.begin]}[/red]"
            print(file_lines[scope.begin])
            """

        return marked_up_lines

    def list_files(self) -> Table:
        name_time_pairs = [
            (str(k), v.stats.host_total, v.stats.device_total)
            for k, v in self.files_dict.items()
        ]
        name_time_pairs = list(sorted(name_time_pairs, key=lambda x: x[1]))

        table = Table(title="File Summary")
        table.add_column("Path", max_width=20, justify="right", no_wrap=False)
        table.add_column("CPU time")
        table.add_column("GPU time")

        for file, gpu, cpu in name_time_pairs:
            table.add_row(file, fmt_time(gpu), fmt_time(cpu))

        return table


class LinesApp(App):
    def __init__(self, *args, viewer: Viewer, **kwargs):
        self.viewer = viewer
        super().__init__(*args, **kwargs)

    async def on_load(self) -> None:
        """Sent before going in to application mode."""

        # Bind our basic keys
        await self.bind("q", "quit", "Quit")
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")

    async def on_mount(self) -> None:
        self.side = side = ScrollView(auto_width=True)
        self.body = body = ScrollView(auto_width=True)

        await self.view.dock(Footer(), edge="bottom")
        await self.view.dock(side, edge="left", size=48, name="sidebar")
        await self.view.dock(body, edge="right", name="code")

        async def add_content():
            files_table = self.viewer.list_files()

            name_time_pairs = [
                (str(k), v.stats.host_total, v.stats.device_total)
                for k, v in self.viewer.files_dict.items()
            ]

            name_time_pairs = list(sorted(name_time_pairs, key=lambda x: x[1]))
            file = name_time_pairs[-1][0]

            code_content = self.viewer.view_file(file)

            await side.update(files_table)
            await body.update("\n".join(code_content))

        await self.call_later(add_content)

    async def action_item_clicked(self, item: str) -> None:
        self.console.bell()
        self.log("checkbox item", item, "clicked")


if __name__ == "__main__":
    import argparse

    logger = get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)
    parser.add_argument(
        "--src",
        type=Path,
        default=None,
        help="Optional path to source directory. Only consider files within, if passed",
    )
    parser.add_argument("--filter_src", type=Path, default=None)

    args = parser.parse_args()

    files_dict = load_traces(args.profile_json, args.src, args.filter_src)

    viewer = Viewer(files_dict)
    LinesApp.run(title="Lines", viewer=viewer)

    """
    console = Console()
    viewer.list_files()

    while True:
        command = console.input("Enter Command > ")

        if command == "ls":
            viewer.list_files()
        elif command.startswith("show"):
            viewer.view_file(command.split(" ")[1])
        else:
            console.print(f"Unknown command {command}")
    """
