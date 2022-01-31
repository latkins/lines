from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from torch_tb_profiler import io
from torch_tb_profiler.profiler import RunLoader

from .log import get_logger

logger = get_logger()


@dataclass
class LineStats:
    """Class to summarise trace info for a line."""

    calls: int
    device_total: float
    host_total: float
    tc_total_ratio: float

    @classmethod
    def from_events(cls, events: List[Dict[str, Any]]) -> LineStats:
        calls = sum([d.get("calls", 0) for d in events])
        device_total = sum([d.get("device_total_duration", 0) for d in events])
        host_total = sum([d.get("host_total_duration", 0) for d in events])
        tc_total_ratio = sum([d.get("tc_total_ratio", 0) for d in events]) / len(events)

        return cls(calls, device_total, host_total, tc_total_ratio)


@dataclass
class ScopeStats:
    calls: int
    device_total: float
    host_total: float

    @classmethod
    def from_lines(cls, line_stats: List[LineStats]) -> ScopeStats:
        return cls(
            sum(line.calls for line in line_stats),
            sum(line.device_total for line in line_stats),
            sum(line.host_total for line in line_stats),
        )


def process_call(call: str) -> Tuple[Path, int, str]:
    file_line, fn = call.rsplit(":")
    file, line = file_line.rsplit("(")

    return Path(file), int(line[:-1]) - 1, fn.strip()


def process_call_stack(call_stack: str) -> List[Tuple[Path, int, str]]:
    call_stack = filter(len, call_stack.split(";"))

    processed_calls = []
    for call in call_stack:
        processed_calls.append(process_call(call))
    return processed_calls


def load_traces(profile_json: Path):
    files_dict = defaultdict(lambda: defaultdict(list))
    cache = io.Cache()

    loader = RunLoader(str(profile_json.name), str(profile_json.parent), cache)

    run = loader.load()
    if len(run.profiles) > 1:
        logger.warn(f"Found {len(run.profiles)} profiles, choosing first.")
    profile = list(run.profiles.values())[0]

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
    files_dict = {
        file: {
            line: LineStats.from_events(call_stack)
            for line, call_stack in lines_dict.items()
        }
        for file, lines_dict in files_dict.items()
    }
    return files_dict
