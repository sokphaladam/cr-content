"""Progress reports from long steps to the job that runs them (the lyric video tab's progress bar).

A step calls report(0.4, "Listening to the song 3/8"); when a job is capturing output, that becomes the job's
`progress` (how far the current step is, 0..1) and `detail`. Outside a job (the command line) it prints nothing.
"""
import threading
from pathlib import Path

PREFIX = "@@ "
enabled = False  # set by the job runner around a run


def report(fraction: float | None, detail: str = "") -> None:
    if enabled:
        print(f"{PREFIX}{'' if fraction is None else f'{max(0.0, min(1.0, fraction)):.3f}'} {detail}".rstrip(), flush=True)


def parse(line: str) -> tuple[float | None, str] | None:
    """(fraction, detail) of a report line, None when `line` isn't one."""
    if not line.startswith(PREFIX):
        return None
    head, _, detail = line[len(PREFIX):].partition(" ")
    try:
        return (float(head) if head else None), detail.strip()
    except ValueError:
        return None


class WatchFile:
    """Reports how much of a file being downloaded has arrived, as a share of `total` bytes, between `lo` and `hi`."""

    def __init__(self, path: Path, total: int, lo: float, hi: float, label: str):
        self.path, self.total, self.lo, self.hi, self.label = path, total, lo, hi, label
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            try:
                done = self.path.stat().st_size
            except OSError:
                continue
            share = min(1.0, done / self.total)
            report(self.lo + (self.hi - self.lo) * share, f"{self.label} {int(share * 100)}% ({done >> 20} of {self.total >> 20} MB)")

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
