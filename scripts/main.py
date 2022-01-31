from collections import defaultdict
from pathlib import Path

import rich

from lines.code import ScopeFinder
from lines.log import get_logger
from lines.process_traces import ScopeStats, load_traces

if __name__ == "__main__":
    import argparse

    logger = get_logger()

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)
    parser.add_argument("source_dir", type=Path)

    args = parser.parse_args()

    python_files = set(args.source_dir.glob("**/*.py"))

    files_dict = load_traces(args.profile_json)

    file_name = Path(
        "/Users/latkins/charm/dragonligandfold/dragonligandfold/experiments/cotrain/model.py"
    )
    lines_dict = files_dict[file_name]
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

            if line_stats.device_total / scope_stats.device_total > 0.5:
                code = f"[red]{code}[/red]"

            stats_str = f"| Scope GPU Time: {line_stats.device_total / scope_stats.device_total:3.0%} | Scope CPU Time: {line_stats.host_total / scope_stats.host_total:3.0%} | Avg. TensorCore Util.: {line_stats.tc_total_ratio:3.0f}%"
        rich.print(f"{code:100} {stats_str}")

    breakpoint()
