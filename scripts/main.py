from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import rich
from rich.console import Console
from rich.pretty import pprint
from rich.syntax import Syntax
from rich.table import Table

from lines.code import ScopeFinder
from lines.log import get_logger
from lines.process_traces import File, load_traces


def fmt_time(time_us: int) -> str:
    if time_us / 1000_000 > 1:
        # Show in s
        return f"{time_us / 1000_000:.2f}s"
    elif (time_us / 1000) > 1:
        return f"{time_us / 1000:.2f}ms"
        # Show in ms
    else:
        return f"{time_us}us"


class Viewer:
    def __init__(self, files_dict, console):
        self.files_dict = files_dict
        self.console = console

    @classmethod
    def build(cls, files_dict, console: Console) -> Viewer:
        processed_file_dict = {}
        for file_name, lines_dict in self.files_dict.items():

            file = File.from_dict(file_name, lines_dict)
            processed_file_dict[file_name] = file

        return cls(processed_file_dict, console)

    def view_file(self, file_name: str):
        file = self.files_dict[file_name]

        lines_dict = file.lines
        finder = file.finder

        scope_dict = defaultdict(list)
        lines_to_scope = {}

        for line_no, line_stats in lines_dict.items():
            scope_dict[finder[line_no]].append(line_stats)
            lines_to_scope[line_no] = finder[line_no]

        # scope_stats_dict = {
        # scope: ScopeStats.from_lines(lines) for scope, lines in scope_dict.items()
        # }

        with file_name.open("r") as f:
            file_lines = f.readlines()

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
        pprint([str(k) for k in sorted(self.files_dict.keys())])


if __name__ == "__main__":
    import argparse

    logger = get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)

    args = parser.parse_args()

    file_dict = load_traces(args.profile_json)

    breakpoint()

    console = Console()
    viewer = Viewer.build(scope_stats, console)

    viewer.list_files()

    while True:
        command = console.input("Enter Command > ")

        if command == "ls":
            viewer.list_files()
        elif command.startswith("show"):
            viewer.view_file(command.split(" ")[1])
        else:
            console.print(f"Unknown command {command}")
