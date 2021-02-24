"""Utility classes/functions to be used in the project."""

import gc
from pathlib import Path
import signal
import timeit

import pandas as pd
from scipy import stats


ROOT_DIR = Path(__file__).parents[1]


class TimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutException


signal.signal(signal.SIGALRM, _timeout_handler)


class Timer:
    def __init__(
        self,
        timer=None,
        disable_gc=False,
        verbose=True,
        timeout=None,
        msg_template="Time taken: %f seconds",
    ):
        if timer is None:
            timer = timeit.default_timer
        self.timer = timer
        self.disable_gc = disable_gc
        self.gc_state = None
        self.verbose = verbose
        self.timeout = timeout
        self.msg_template = msg_template
        self.start = self.end = self.interval = None

    def __enter__(self):
        if self.disable_gc:
            self.gc_state = gc.isenabled()
            gc.disable()
        if self.timeout is not None:
            signal.alarm(self.timeout)  # set the alarm
        self.start = self.timer()
        return self

    def __exit__(self, *args):
        self.end = self.timer()
        if self.timeout is not None:
            signal.alarm(0)  # clear the alarm in case it has not been activated
        if self.disable_gc and self.gc_state:
            gc.enable()
            self.gc_state = None
        self.interval = self.end - self.start
        if self.verbose:
            print(self.msg_template % self.interval)


def load_graph_index(dataset_id: str) -> pd.DataFrame:
    outputs_folder = ROOT_DIR / "outputs" / dataset_id
    graphs_index_filepath = outputs_folder / "graphs.pickled"
    timings_filepath = outputs_folder / "timings.pickled"

    graphs_index = pd.read_pickle(graphs_index_filepath)  # type: pd.Dataframe
    timings = pd.read_pickle(timings_filepath)  # type: pd.Dataframe
    timings = timings.rename(
        lambda col_name: "timings_" + col_name, axis="columns", copy=False
    )
    return graphs_index.join(timings, on="graph_file")


def ranksums(
    df: pd.DataFrame,
    methods,
    scoring="accuracy",
    pvalue_significant=0.05,
    verbose=False,
):
    # returns None if the difference between the two methods is not statistically significant
    # according to the ranksums test; otherwise, returns the mean difference value.

    assert len(methods) == 2
    assert scoring in df.columns

    if verbose:
        print("Wilcoxon rank-sum test:", scoring)
        print(f"> Comparing {methods[0]} vs {methods[1]}")

    p1 = df[df.method == methods[0]]
    p1.reset_index(inplace=True)
    p1_mean = p1[scoring].mean()

    p2 = df[df.method == methods[1]]
    p2.reset_index(inplace=True)
    p2_mean = p2[scoring].mean()

    mean_diff = p1_mean - p2_mean
    _, pvalue = stats.ranksums(p1[scoring], p2[scoring])
    if pvalue > pvalue_significant:
        if verbose:
            print(f"> Insignificant (pvalue = {pvalue * 100:.1f}%)")
        return None
    else:
        if verbose:
            print(f"> *Significant* (pvalue = {pvalue * 100:.1f}%)")
            print(f"> Mean difference: {mean_diff * 100:+.1f}%")
        return mean_diff
