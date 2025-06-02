import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response
from scipy.optimize import curve_fit

from atomate2.dmax.jobs.dma_parser import sin_func
from atomate2.dmax.schemas.task import DmaxNumCyclesConvergenceFlowDocument


def _parse_input_vars(input_script):
    amp_pc = None
    period = None
    axis = None
    dt_fs = None
    with open(input_script) as f:
        for line in f:
            parts = line.strip().split()
            if parts[:3] == ['variable', 'oap', 'equal'] and '*' in parts[-1]:
                amp_pc = float(parts[-1].split('*')[0])
            if parts[:3] == ['variable', 'period', 'equal']:
                period = int(parts[-1])
            if parts[:3] == ['variable', 'timestep', 'equal']:
                dt_fs = float(parts[-1])
            if parts and parts[0] == 'fix' and 'deform' in parts:
                idx = parts.index('deform')
                if len(parts) > idx + 2:
                    axis = parts[idx + 2]
    if amp_pc is None or period is None or axis is None or dt_fs is None:
        raise RuntimeError(f"Failed to parse required vars from {input_script}")
    # convert percentage amplitude
    if amp_pc > 1.0:
        amp_pc /= 100.0
    return amp_pc, period, axis, dt_fs


def _load_dma_dataframe(log_path, input_script):
    # get thermo_style labels
    labels = None
    with open(input_script) as f:
        for line in f:
            parts = line.strip().split()
            if parts and parts[0] == 'thermo_style':
                labels = parts[2:] if parts[1] == 'custom' else parts[1:]
                break
    if not labels:
        raise RuntimeError(f"Could not find thermo_style in {input_script}")
    # read log
    with open(log_path, encoding='utf-8', errors='ignore') as fh:
        lines = fh.readlines()
    # locate start of DMA section
    start = next((i for i, l in enumerate(lines) if 'NPT Dynamic Mechanical Analysis' in l), 0)
    data = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped and stripped[0].isdigit():
            vals = stripped.split()
            if len(vals) == len(labels):
                data.append([float(v) for v in vals])
    df = pd.DataFrame(data, columns=labels)
    return df


def _get_log_path(work_dir):
    # find first .log file
    logs = [f for f in os.listdir(work_dir) if f.endswith('.log')]
    if not logs:
        raise FileNotFoundError(f"LAMMPS log file not found in {work_dir}")
    return os.path.join(work_dir, logs[0])


@dataclass
class NumCyclesConvergenceMaker(Maker):
    """
    Maker to analyze tan δ convergence over increasing cycle count.
    """
    name: str = 'num_cycles_convergence'
    threshold: float = 0.01

    @job(output_schema=DmaxNumCyclesConvergenceFlowDocument)
    def make(self, work_dir: str) -> Response:
        # locate I/O files
        input_script = os.path.join(work_dir, 'in.lammps')
        log_path = _get_log_path(work_dir)
        # parse input variables
        amp_pc, period, axis, dt_fs = _parse_input_vars(input_script)
        # compute timestep and cycle duration
        cycle_time_fs = period * dt_fs
        omega = 2 * np.pi / period
        # get box length for max_strain
        lengths = {}
        with open(log_path, encoding='utf-8', errors='ignore') as logf:
            for line in logf:
                if 'orthogonal box' in line:
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", line)
                    if len(nums) >= 6:
                        lo = [float(n) for n in nums[:3]]
                        hi = [float(n) for n in nums[3:6]]
                        lengths = dict(zip(['x','y','z'], [hi[i] - lo[i] for i in range(3)]))
                    break
        L0 = lengths.get(axis, 1.0)
        max_strain = amp_pc * L0
        # load DMA dataframe
        df = _load_dma_dataframe(log_path, input_script)
        t = df['time'].to_numpy()
        # stress label
        stress_label = f'p{axis}{axis}'
        if stress_label not in df.columns:
            cand = [col for col in df.columns if col.startswith('p') and col not in ('pe','press')]
            if cand:
                stress_label = cand[0]
            else:
                raise KeyError(f"No stress column found for axis {axis}")
        p = df[stress_label].to_numpy()
        p = p - p.mean()
        # compute total number of cycles
        total_cycles = int(np.floor(t.max() / cycle_time_fs))
        num_cycles = list(range(1, total_cycles + 1))
        tan_deltas = []
        for m in num_cycles:
            # select data for first m cycles
            mask = t <= m * cycle_time_fs
            t_m = t[mask]
            p_m = p[mask]
            # fit sine to pressure
            guess_A = np.max(p_m) - np.min(p_m)
            guess_phi = 0.0
            popt, _ = curve_fit(lambda tt, A, phi: sin_func(tt, A, phi, omega), t_m, p_m, p0=[guess_A, guess_phi])
            A_fit, phi_fit = popt
            # compute moduli
            phase_rad = phi_fit % (2 * np.pi)
            A_MPa = abs(A_fit * 0.101325)
            E_storage = A_MPa / max_strain * np.cos(phase_rad)
            E_loss = A_MPa / max_strain * np.sin(phase_rad)
            tan_deltas.append(float(E_loss / E_storage) if E_storage != 0 else None)
        # select optimal cycle count based on threshold
        optimal = num_cycles[-1]
        for i in range(1, len(tan_deltas)):
            if tan_deltas[i-1] is not None and tan_deltas[i] is not None:
                rel_diff = abs(tan_deltas[i] - tan_deltas[i-1]) / abs(tan_deltas[i])
                if rel_diff < self.threshold:
                    optimal = num_cycles[i]
                    break
        # plot tan_delta vs cycle count
        plot_file = os.path.join(os.getcwd(), 'tan_delta_vs_cycles.png')
        plt.figure()
        plt.plot(num_cycles, tan_deltas, 'o-')
        plt.xlabel('Number of cycles')
        plt.ylabel('tan δ')
        plt.axvline(optimal, color='r', linestyle='--', label=f'Optimal = {optimal}')
        plt.legend()
        plt.tight_layout()
        plt.savefig(plot_file)
        plt.close()
        # return document
        return Response(
            output=DmaxNumCyclesConvergenceFlowDocument(
                num_cycles=num_cycles,
                tan_delta=tan_deltas,
                threshold=self.threshold,
                optimal_num_cycles=optimal,
                plot=plot_file,
            )
        )
