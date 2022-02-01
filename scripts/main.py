from collections import defaultdict
from pathlib import Path

import rich
from rich.pretty import pprint

from lines.code import ScopeFinder
from lines.log import get_logger
from lines.process_traces import ScopeStats, load_traces


def fmt_time(time_us: int) -> str:
    if (time_us / 1000) > 1:
        return f"{time_us / 1000:.2f}ms"
        # Show in ms
    elif time_us / 1000_000 > 1:
        # Show in s
        return f"{time_us / 1000_000:.2f}s"
    else:
        return f"{time_us}us"


class Viewer:
    def __init__(self, files_dict):
        self.files_dict = files_dict

    def make_scope_dicts(self):
        scope_dicts = {}

        for file_name, lines_dict in self.files_dict.items():

            scope_dict = defaultdict(list)
            lines_to_scope = {}

            for line_no, line_stats in lines_dict.items():
                scope_dict[finder[line_no]].append(line_stats)
                lines_to_scope[line_no] = finder[line_no]

            scope_stats_dict = {
                scope: ScopeStats.from_lines(lines)
                for scope, lines in scope_dict.items()
            }

    def view_file(self, file_name: str):
        file_name = Path(file_name)
        lines_dict = self.files_dict[file_name]
        finder = ScopeFinder(file_name)

        scope_dict = defaultdict(list)
        lines_to_scope = {}

        for line_no, line_stats in lines_dict.items():
            scope_dict[finder[line_no]].append(line_stats)
            lines_to_scope[line_no] = finder[line_no]

        scope_stats_dict = {
            scope: ScopeStats.from_lines(lines) for scope, lines in scope_dict.items()
        }

        print(file_name)
        with file_name.open("r") as f:
            file_lines = f.readlines()

        for i, file_line in enumerate(file_lines):
            code = file_line.rstrip()
            stats_str = ""

            if i in lines_dict:
                scope_stats = scope_stats_dict[lines_to_scope[i]]
                line_stats = lines_dict[i]

                if (
                    scope_stats.device_total
                    and (line_stats.device_total / scope_stats.device_total) > 0.5
                ):
                    code = f"[red]{code}[/red]"

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

                stats_str = f"| GPU: {gpu_time} ({gpu_p:3.0%}) | CPU: {cpu_time} ({cpu_p:3.0%}) | Avg. TensorCore Util.: {avg_tc:3.0f}%"
            rich.print(f"{code:100} {stats_str}")

    def show_files(self) -> None:
        pprint([str(k) for k in sorted(self.files_dict.keys())])


if __name__ == "__main__":
    import argparse

    logger = get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)

    args = parser.parse_args()

    files_dict = load_traces(args.profile_json)

    viewer = Viewer(files_dict)

    viewer.show_files()

    while True:
        command = input("Enter Command > ")

        if command == "ls":
            viewer.show_files()
        elif command.startswith("show"):

            viewer.view_file(command.split(" ")[1])
        else:
            pprint("Unknown command {command}")
