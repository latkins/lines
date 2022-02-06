from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Union

from rich.console import Console
from rich.pretty import pprint
from rich.table import Table

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


class Viewer:
    def __init__(self, files_dict: Dict[Path, File], console):
        self.files_dict = files_dict
        self.console = console

    def view_file(self, file_name: str):
        file = self.files_dict[Path(file_name)]

        # lines_dict = file.line
        # finder = file.finder

        # scope_dict = defaultdict(list)
        # lines_to_scope = {}

        # for line_no, line_stats in lines_dict.items():
        # scope_dict[finder[line_no]].append(line_stats)
        # lines_to_scope[line_no] = finder[line_no]

        # scope_stats_dict = {
        # scope: ScopeStats.from_lines(lines) for scope, lines in scope_dict.items()
        # }

        with Path(file_name).open("r") as f:
            file_lines = [line.rstrip() for line in f.readlines()]

        for scope in file.scope.items():
            if scope.data.stats.calls == 0:
                for i in range(scope.begin, scope.end):
                    file_lines[i] = f"[grey]{file_lines[i]}[/grey]"
                continue
            file_lines[scope.begin - 1] = f"[red]{file_lines[scope.begin]}[/red]"
            print(file_lines[scope.begin])

        # for file_line in file_lines:
        # self.console.print(file_line)
        return

        breakpoint()

        table = Table(title=str(file_name))

        table.add_column("Line")
        table.add_column("Code")
        table.add_column("GPU")
        table.add_column("CPU")
        table.add_column("TensorCores")

        for i, file_line in enumerate(file_lines):
            gpu_cell = ""
            cpu_cell = ""
            tc_cell = ""
            if i in lines_dict:
                scope_stats = scope_stats_dict[lines_to_scope[i]]
                line_stats = lines_dict[i]

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

            table.add_row(str(i), file_line.rstrip(), gpu_cell, cpu_cell, tc_cell)
        self.console.print(table)

    def list_files(self) -> None:
        name_time_pairs = [
            (str(k), v.stats.host_total, v.stats.device_total)
            for k, v in self.files_dict.items()
        ]
        name_time_pairs = list(sorted(name_time_pairs, key=lambda x: x[1]))

        table = Table(title="File Summary")
        table.add_column("Path", no_wrap=False)
        table.add_column("CPU time")
        table.add_column("GPU time")

        for file, gpu, cpu in name_time_pairs:
            table.add_row(file, fmt_time(gpu), fmt_time(cpu))

        self.console.print(table, style="bold bright_green on black")


if __name__ == "__main__":
    import argparse

    logger = get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)

    args = parser.parse_args()

    files_dict = load_traces(args.profile_json)

    console = Console()
    viewer = Viewer(files_dict, console)

    viewer.list_files()

    while True:
        command = console.input("Enter Command > ")

        if command == "ls":
            viewer.list_files()
        elif command.startswith("show"):
            viewer.view_file(command.split(" ")[1])
        else:
            console.print(f"Unknown command {command}")
