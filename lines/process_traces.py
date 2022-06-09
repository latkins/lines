from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from intervaltree import IntervalTree
from torch_tb_profiler import io
from torch_tb_profiler.profiler import RunLoader

from .code import ScopeFinder
from .log import get_logger

logger = get_logger()

Event = Dict[str, Any]


@dataclass
class Stats:
    calls: int
    device_total: float
    host_total: float
    tc_total_ratio: float

    @classmethod
    def from_events(cls, events: List[Dict[str, Any]]) -> Stats:
        calls = sum([d.get("calls", 0) for d in events])
        device_total = sum([d.get("device_total_duration", 0) for d in events])
        host_total = sum([d.get("host_total_duration", 0) for d in events])
        tc_total_ratio = sum([d.get("tc_total_ratio", 0) for d in events]) / len(events)

        return cls(calls, device_total, host_total, tc_total_ratio)

    @classmethod
    def combine(cls, stats: List[Stats]) -> Stats:
        calls = sum(s.calls for s in stats)
        device_total = sum(s.device_total for s in stats)
        host_total = sum(s.host_total for s in stats)
        if len(stats):
            tc_total_ratio = sum(s.host_total for s in stats) / len(stats)
        else:
            tc_total_ratio = 0

        return cls(calls, device_total, host_total, tc_total_ratio)


# Look up stats based on line.
class LineLookup:
    def __init__(self, lines_dict: Dict[int, Stats]):
        self.lines_dict = lines_dict

    @classmethod
    def from_line_to_event(cls, line_to_event: Dict[int, List[Event]]) -> LineLookup:
        return cls(
            {
                line: Stats.from_events(call_stack)
                for line, call_stack in line_to_event.items()
            }
        )

    def __getitem__(self, line: int) -> Optional[Stats]:
        return self.lines_dict.get(line, None)

    def __iter__(self):
        for stats in self.lines_dict.values():
            yield stats

    def items(self):
        return self.lines_dict.items()

    def values(self):
        return self.lines_dict.values()


@dataclass
class Scope:
    name: Optional[str]
    stats: Stats
    line_lookup: LineLookup


@dataclass
class File:
    stats: Stats
    line: LineLookup
    finder: ScopeFinder
    scope: IntervalTree

    @classmethod
    def from_dict(
        cls, file_name: Path, line_events_dict: Dict[int, List[Event]]
    ) -> File:
        finder = ScopeFinder(file_name)
        line_lookup = LineLookup.from_line_to_event(line_events_dict)

        file_stats = Stats.combine(list(line_lookup.values()))

        scope_tree = IntervalTree()
        for interval in finder.tree:
            # line_stats in this range?
            # summary stats
            scope_lines: Dict[int, Stats] = {}
            for i in range(interval.begin, interval.end):
                line_stats = line_lookup[i]
                if line_stats:
                    scope_lines[line_lookup] = line_stats
            scope_stats = Stats.combine(list(scope_lines.values()))

            scope_tree[interval.begin : interval.end] = Scope(
                finder[interval.begin], scope_stats, LineLookup(scope_lines)
            )

        return cls(file_stats, line_lookup, finder, scope_tree)

    # scope is just a range of lines?
    # Would like summary stats for each scope.


def process_call(call: str) -> Tuple[Path, int, str]:
    file_line, fn = call.rsplit(":")
    file, line = file_line.rsplit("(")

    return Path(file), int(line[:-1]) - 1, fn.strip()


def process_call_stack(call_stack: str) -> List[Tuple[Path, int, str]]:
    call_stack_list = list(filter(len, call_stack.split(";")))

    processed_calls = []
    for call in call_stack_list:
        try:
            processed_calls.append(process_call(call))
        except ValueError:
            logger.debug(f"could not process {call}, skipping")
    return processed_calls


def make_absolute(file_dict: Dict[Path, Any], src: Path) -> Dict[Path, Any]:
    """Keys in `files_dict` may be relative. Make these absolute, if those files exist."""
    for k in list(file_dict.keys()):
        absolute = src / k
        if absolute.exists():
            file_dict[absolute] = file_dict[k]
            del file_dict[k]
    return file_dict


def replace_paths(
    file_dict: Dict[Path, Any],
    src: Path,
    filter_src: Path,
) -> Dict[Path, Any]:
    """Look for files"""

    # Look for files in file_dict relative to filter_src, replace them with files from src
    for k in list(file_dict.keys()):
        try:
            rel = k.relative_to(str(filter_src))
        except ValueError:
            logger.info(f"Couldn't find file relative to {filter_src} for {k}")
        else:
            renamed = src / rel
            if renamed == k:
                continue

            if renamed.exists():
                file_dict[renamed] = file_dict[k]
                logger.info(f"Renamed {k} to {renamed}")

        del file_dict[k]

    return file_dict


def load_traces(
    profile_json: Path, src: Optional[Path] = None, filter_src: Optional[Path] = None
) -> Dict[Path, File]:
    """
    Ultimately return for each profile?
    """
    files_dict = defaultdict(lambda: defaultdict(list))
    cache = io.Cache()

    loader = RunLoader(str(profile_json.name), str(profile_json.parent), cache)

    run = loader.load()

    keys = run.profiles.keys()
    name_root = str(profile_json.name).split(".")[0]
    valid_keys = [k for k in keys if k[0].startswith(name_root)]

    if len(run.profiles) > 1:
        logger.warn(f"Found {len(run.profiles)} profiles, choosing {valid_keys[-1]}.")

    profile = run.profiles[valid_keys[-1]]

    stack = profile.operation_stack_by_name

    # Link stats to file/line.
    for op_name, data_dict in stack.items():
        logger.info(f"processing {op_name}")
        if "data" not in data_dict:
            continue
        data = data_dict["data"]

        for call in data:
            processed_stack = process_call_stack(call["call_stack"])
            for (file, line_no, method) in processed_stack:
                files_dict[file][line_no].append(call)

    if src:
        files_dict = make_absolute(files_dict, src)

    if src and filter_src:
        files_dict = replace_paths(files_dict, src, filter_src)

    return {
        file_path: File.from_dict(file_path, lines_dict)
        for file_path, lines_dict in files_dict.items()
    }
