import os
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from jobflow import Maker, Response, job
from scipy.optimize import curve_fit
from sklearn.metrics import mean_squared_error, r2_score

from atomate2.dmax.schemas.task import (
    DmaxDmaParserDocument,
    DmaxLammpsInputDocument,
    DmaxLammpsRunDocument,
)


def sin_func(t, A, phi, omega):
    return A * np.sin(omega * t + phi)


@dataclass
class DmaParserMaker(Maker):
    """
    Maker to parse outputs from dynamic mechanical analysis: storage/loss moduli and elastic modulus.
    """

    name: str = "dma_parser"

    @job(output_schema=DmaxDmaParserDocument)
    def make(
        self,
        input_doc: DmaxLammpsInputDocument,
        run_doc: DmaxLammpsRunDocument,
    ) -> Response:
        wd = input_doc.input_dir
        # locate input script and log
        input_script = os.path.join(wd, input_doc.input_file)
        logs = [f for f in os.listdir(wd) if f.endswith(".log")]
        log_file = logs[0] if logs else None
        if not log_file:
            raise FileNotFoundError("LAMMPS log file not found in " + wd)
        log_path = os.path.join(wd, log_file)

        # parse input script to extract amplitude, period, and deformation axis
        amp_pc = None
        period = None
        axis = None
        temperature_val = None
        pressure_val = None
        dt_fs = None
        with open(input_script) as f:
            for line in f:
                parts = line.strip().split()
                # temperature variable
                if parts[:3] == ["variable", "temperature", "equal"]:
                    temperature_val = float(parts[-1])
                # pressure variable
                if parts[:3] == ["variable", "pressure", "equal"]:
                    pressure_val = float(parts[-1])
                # timestep variable for dt (in fs)
                if parts[:3] == ["variable", "timestep", "equal"]:
                    dt_fs = float(parts[-1])
                # amplitude variable: variable oap equal <value>*
                if parts[:3] == ["variable", "oap", "equal"] and "*" in parts[-1]:
                    amp_pc = float(parts[-1].split("*")[0])
                # period variable
                if parts[:3] == ["variable", "period", "equal"]:
                    period = int(parts[-1])
                # deform command contains axis: fix <id> all deform 1 <axis> wiggle ...
                if parts and parts[0] == "fix" and "deform" in parts:
                    idx = parts.index("deform")
                    if len(parts) > idx + 2:
                        axis = parts[idx + 2]
        if (
            amp_pc is None
            or period is None
            or axis is None
            or temperature_val is None
            or pressure_val is None
            or dt_fs is None
        ):
            raise RuntimeError(f"Failed to parse required vars from {input_script}")
        # convert percentage amplitude to fraction if necessary
        if amp_pc > 1.0:
            amp_pc /= 100.0
        # assign defaults
        max_strain = 0.0  # will compute after box lengths
        # compute oscillation frequency (Hz) from period and timestep
        dt_s = dt_fs * 1e-15  # fs to s
        frequency_val = 1.0 / (period * dt_s)

        # get box lengths from log file's orthogonal box line
        import re

        lengths = {}
        with open(log_path, encoding="utf-8", errors="ignore") as logf:
            for line in logf:
                if "orthogonal box" in line:
                    # extract six floats: xlo ylo zlo xhi yhi zhi
                    nums = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", line)
                    if len(nums) >= 6:
                        lo = [float(n) for n in nums[:3]]
                        hi = [float(n) for n in nums[3:6]]
                        lengths = dict(
                            zip(["x", "y", "z"], [hi[i] - lo[i] for i in range(3)])
                        )
                        break
        L0 = lengths.get(axis, 1.0)
        max_strain = amp_pc * L0

        # parse thermo data from log
        labels = None
        with open(input_script) as f_in:
            for line in f_in:
                parts = line.strip().split()
                if parts and parts[0] == "thermo_style":
                    # parts: ['thermo_style', 'custom', ...]
                    labels = parts[2:] if parts[1] == "custom" else parts[1:]
                    break
        if not labels:
            raise RuntimeError(f"Could not find thermo_style in {input_script}")
        # parse thermo data only after the DMA section begins
        with open(log_path, encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
        # locate start of NPT Dynamic Mechanical Analysis section
        dma_start = next(
            (i for i, l in enumerate(lines) if "NPT Dynamic Mechanical Analysis" in l),
            0,
        )
        data = []
        for line in lines[dma_start:]:
            stripped = line.strip()
            if stripped and stripped[0].isdigit():
                vals = stripped.split()
                if len(vals) == len(labels):
                    data.append([float(v) for v in vals])
        df = pd.DataFrame(data, columns=labels)
        # time in fs
        t = df["time"].to_numpy()
        # stress based on axis, with fallback
        stress_label = f"p{axis}{axis}"
        if stress_label not in df.columns:
            # fallback to first pressure component in columns
            cand = [
                col
                for col in df.columns
                if col.startswith("p") and col not in ("pe", "press")
            ]
            if cand:
                stress_label = cand[0]
            else:
                raise KeyError(f"No stress column found for axis {axis}")
        p = df[stress_label].to_numpy()
        p -= p.mean()

        # angular frequency rad/fs
        omega = 2 * np.pi / period
        # initial guesses
        guess_A = np.max(p) - np.min(p)
        guess_phi = 0.0
        popt, _ = curve_fit(
            lambda tt, A, phi: sin_func(tt, A, phi, omega),
            t,
            p,
            p0=[guess_A, guess_phi],
        )
        A_fit, phi_fit = popt
        fit_curve = sin_func(t, A_fit, phi_fit, omega)

        # compute metrics
        phase_rad = phi_fit % (2 * np.pi)
        phase_deg = np.degrees(phase_rad)
        phase_magnitude = "Lagging" if phi_fit >= 0 else "Leading"
        r2 = r2_score(p, fit_curve)
        rmse = np.sqrt(mean_squared_error(p, fit_curve))

        # convert stress satm to MPa (1 atm = 0.101325 MPa)
        A_MPa = abs(A_fit * 0.101325)
        # storage and loss moduli
        E_storage = A_MPa / max_strain * np.cos(phase_rad)
        E_loss = A_MPa / max_strain * np.sin(phase_rad)
        tan_delta = E_loss / E_storage if E_storage != 0 else None

        # elastic modulus via stress vs strain slope
        strain_curve = amp_pc * np.sin(omega * t)
        slope, _ = np.polyfit(strain_curve, p * 0.101325, 1)
        E_elastic = slope

        # Poisson ratio via box length variations along x, y, z
        Lx = df["lx"].to_numpy()
        Ly = df["ly"].to_numpy()
        Lz = df["lz"].to_numpy()
        # initial lengths
        Lx0, Ly0, Lz0 = Lx[0], Ly[0], Lz[0]
        # compute strains
        strain_x = (Lx - Lx0) / (Lx0 + 1e-8)
        strain_y = (Ly - Ly0) / (Ly0 + 1e-8)
        strain_z = (Lz - Lz0) / (Lz0 + 1e-8)
        # identify axial direction based on max oscillation magnitude
        dLx = np.abs(np.diff(Lx))
        dLy = np.abs(np.diff(Ly))
        dLz = np.abs(np.diff(Lz))
        max_diff = max(dLx.max(), dLy.max(), dLz.max())
        if dLy.max() == max_diff:
            axial_strain, lateral1_strain, lateral2_strain = (
                strain_y,
                strain_x,
                strain_z,
            )
        elif dLx.max() == max_diff:
            axial_strain, lateral1_strain, lateral2_strain = (
                strain_x,
                strain_y,
                strain_z,
            )
        else:
            axial_strain, lateral1_strain, lateral2_strain = (
                strain_z,
                strain_x,
                strain_y,
            )
        # compute Poisson time series and average
        eps = 1e-8
        valid_ax = np.abs(axial_strain) > eps
        nu1 = np.full_like(axial_strain, np.nan)
        nu2 = np.full_like(axial_strain, np.nan)
        nu1[valid_ax] = -lateral1_strain[valid_ax] / axial_strain[valid_ax]
        nu2[valid_ax] = -lateral2_strain[valid_ax] / axial_strain[valid_ax]
        nu_avg_ts = np.nanmean(np.vstack([nu1, nu2]), axis=0)
        avg_poisson = np.nanmean(nu_avg_ts)

        # plots: pressure vs time with data, original and fitted curves
        conv = 0.101325  # atm to MPa conversion
        pressure_plot = os.path.join(wd, "dma_pressure_fit.png")
        fig, ax = plt.subplots()
        # scatter raw pressure data
        ax.scatter(t, -p * conv, s=5, alpha=0.5, label="Pressure data")
        # original sinusoidal signal (zero-phase)
        orig_curve = A_fit * np.sin(omega * t)
        ax.plot(t, -orig_curve * conv, "b--", label="Original signal")
        # fitted sinusoidal curve
        ax.plot(t, -fit_curve * conv, "r-", label="Fitted sinusoidal")
        ax.set_xlabel("Time (fs)")
        ax.set_ylabel("Pressure (MPa)")
        # title showing temperature, pressure, frequency in MHz, and strain
        ax.set_title(
            f"Pressure fit: {temperature_val}K, {pressure_val} atm, {frequency_val * 1e-6:.2f} MHz, {amp_pc * 100:.1f}% strain"
        )
        ax.legend()
        # metrics textbox
        rmse_mpa = rmse * conv
        textstr = "\n".join(
            [
                f"R²: {r2:.3f}",
                f"RMSE: {rmse_mpa:.1f} MPa",
                f"E' (storage): {E_storage:.1f} MPa",
                f"E'' (loss): {E_loss:.1f} MPa",
                f"tan δ: {tan_delta:.3f}" if tan_delta is not None else "tan δ: N/A",
                f"Phase angle: {phase_deg:.1f}º",
            ]
        )
        ax.text(
            0.02,
            0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        )
        fig.tight_layout()
        fig.savefig(pressure_plot)
        plt.close(fig)

        # plot stress-strain ellipse: pressure fit vs displacement
        stress_strain_plot = os.path.join(wd, "dma_stress_strain_ellipse.png")
        fig3, ax3 = plt.subplots()
        # actual displacement along deformation axis
        disp = strain_curve * L0
        # fitted pressure in MPa (inverted)
        fit_pressure = -fit_curve * conv
        # compute major-axis slope as elastic energy via linear regression
        slope_ellipse, intercept = np.polyfit(disp, fit_pressure, 1)
        ax3.plot(disp, fit_pressure, ".", alpha=0.5)
        # plot major-axis PCA line
        x_line = np.array([disp.min(), disp.max()])
        y_line = slope_ellipse * x_line + intercept
        ax3.plot(x_line, y_line, "k--", label="Major axis")
        # annotate slope (elastic energy)
        ax3.text(
            0.05,
            0.95,
            f"Elastic energy (slope): {slope_ellipse:.2f} MPa",
            transform=ax3.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.7),
        )
        ax3.set_xlabel(f"Displacement along {axis} (\u212b)")
        ax3.set_ylabel("Pressure (MPa)")
        ax3.set_title("Stress-strain ellipse")
        fig3.tight_layout()
        fig3.savefig(stress_strain_plot)
        plt.close(fig3)

        # plot box-length strains and annotate average Poisson ratio
        poisson_plot = os.path.join(wd, "dma_poisson_vs_time.png")
        fig2, ax2 = plt.subplots()
        ax2.plot(t, strain_x, label="ΔLx/Lx0")
        ax2.plot(t, strain_y, label="ΔLy/Ly0")
        ax2.plot(t, strain_z, label="ΔLz/Lz0")
        ax2.set_xlabel("Time (fs)")
        ax2.set_ylabel("Normalized length change")
        ax2.set_title(f"Box strains; avg Poisson: {avg_poisson:.3f}")
        ax2.legend()
        fig2.tight_layout()
        fig2.savefig(poisson_plot)
        plt.close(fig2)

        return Response(
            output=DmaxDmaParserDocument(
                storage_modulus=E_storage,
                loss_modulus=E_loss,
                tan_delta=tan_delta,
                elastic_modulus=E_elastic,
                poisson_ratio=avg_poisson,
                phase_angle_rad=phase_rad,
                phase_angle_deg=phase_deg,
                fit_r2=r2,
                fit_rmse=rmse,
                amplitude=A_MPa,
                pressure_plot=pressure_plot,
                stress_strain_plot=stress_strain_plot,
            )
        )

    @job(output_schema=DmaxDmaParserDocument)
    def parse_directory(self, work_dir: str) -> Response:
        """
        Debug helper: parse DMA outputs from an existing directory containing in.lammps and log file.
        """
        # build minimal input and run docs
        input_doc = DmaxLammpsInputDocument(
            input_dir=work_dir,
            data_file="",
            input_file="in.lammps",
            slurm_file="",
        )
        run_doc = DmaxLammpsRunDocument(job_id="", restart_file="")
        # call core make logic directly
        return DmaParserMaker.make.__wrapped__(self, input_doc, run_doc)
