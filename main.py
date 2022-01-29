from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Union

import ujson as json
from torch_tb_profiler.profiler.trace import (
    BaseEvent,
    DurationEvent,
    KernelEvent,
    MemoryEvent,
    OperatorEvent,
    ProfilerStepEvent,
    create_trace_event,
)
from tqdm import tqdm

Events = Union[
    DurationEvent, KernelEvent, OperatorEvent, ProfilerStepEvent, MemoryEvent
]


def process_call(call: str) -> Tuple[Path, int, str]:
    file_line, fn = call.rsplit(":")
    file, line = file_line.rsplit("(")

    return Path(file), int(line[:-1]), fn.strip()


def process_call_stack(call_stack: str) -> List[Tuple[Path, int, str]]:
    call_stack = filter(len, call_stack.split(";"))

    processed_calls = []
    for call in call_stack:
        processed_calls.append(process_call(call))
    return processed_calls


def extract_events(data: Dict[str, Any]) -> Iterable[Events]:

    for event in data["traceEvents"]:

        parsed = create_trace_event(event)
        if parsed:
            yield parsed


"""
if "args" not in event or "Call stack" not in event["args"]:
    continue

processed.append((process_call_stack(event["args"]["Call stack"]), event))
"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("profile_json", type=Path)
    parser.add_argument("source_dir", type=Path)

    args = parser.parse_args()

    python_files = list(args.source_dir.glob("**/*.py"))

    with args.profile_json.open("r") as f:
        data = json.load(f)

    # processed_events = extract_events(data)

    # Match trace to file.

    files_dict = {path: defaultdict(list) for path in python_files}

    for event in extract_events(data):
        if not isinstance(event, OperatorEvent):
            print(event)
            breakpoint()
            continue

    # for processed_stack, event in tqdm(processed_events):
    # for (trace_path, line, method) in processed_stack:
    # if trace_path not in python_files:
    # continue

    # if not isinstance(event, dict):
    # print(trace_path, line, type(event))
    # files_dict[trace_path][line].append(event)

    cats = set()
    for file, file_dict in files_dict.items():
        for line, line_traces in file_dict.items():
            for trace in line_traces:
                cats.add(trace["cat"])

    breakpoint()
