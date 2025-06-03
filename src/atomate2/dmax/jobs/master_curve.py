import os
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response
from scipy.interpolate import interp1d
from math import log10
import csv

from atomate2.dmax.schemas.task import DmaxMasterCurveFlowDocument
from atomate2.dmax.schemas.task import DmaxDmaParserDocument

@dataclass
class MasterCurvePlotMaker(Maker):
    """Maker to construct a master curve using WLF shift factors"""
    name: str = 'master_curve_plot'

    @job(output_schema=DmaxMasterCurveFlowDocument)
    def make(
        self,
        parser_docs: list[DmaxDmaParserDocument],
        temperatures: list[float],
        freqs_ghz: list[float],
        reference_temp: float,
    ) -> Response:
        # reshape metrics into arrays
        n_temps = len(temperatures)
        n_freqs = len(freqs_ghz)
        storages = np.array([d.storage_modulus for d in parser_docs], dtype=float).reshape(n_temps, n_freqs)
        losses = np.array([d.loss_modulus for d in parser_docs], dtype=float).reshape(n_temps, n_freqs)
        tans = np.array([d.tan_delta or np.nan for d in parser_docs], dtype=float).reshape(n_temps, n_freqs)
        elastics = np.array([d.elastic_modulus for d in parser_docs], dtype=float).reshape(n_temps, n_freqs)
        poissons = np.array([d.poisson_ratio for d in parser_docs], dtype=float).reshape(n_temps, n_freqs)
        temps = np.array(temperatures, dtype=float)
        freqs_hz = np.array(freqs_ghz, dtype=float) * 1e9
        # define WLF parameter sets
        wlf_params = {'WLF1': (17.44, 51.6), 'WLF2': (8.86, 101.6)}
        # CSV output
        cwd = os.getcwd()
        csv_file = os.path.join(cwd, 'master_curve_data.csv')
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['temperature', 'frequency_ghz', 'storage_modulus', 'loss_modulus', 'tan_delta', 'elastic_modulus', 'poisson_ratio'])
            for i, T in enumerate(temperatures):
                for j, fghz in enumerate(freqs_ghz):
                    writer.writerow([T, fghz, storages[i,j], losses[i,j], tans[i,j], elastics[i,j], poissons[i,j]])
        # master curve plot
        plots = {}
        plt.figure(figsize=(6,4))
        # prepare container for combined master curve data
        combined_curves: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        # scatter shifted data points (master curve)
        for i in range(n_temps):
            # compute shift factor using WLF eqn (positive sign per image)
            # note: will use C1,C2 inside loop later; here just gather unshifted storage positions for reference
            pass  # placeholder; actual scatter below per WLF curves
        # for each WLF set, shift and interpolate
        for key, (C1, C2) in wlf_params.items():
            # compute shift factors
            # use WLF: log10(aT) = C1*(T - T_ref)/(C2 + (T - T_ref))
            aT = 10 ** (C1 * (temps - reference_temp) / (C2 + temps - reference_temp))
            # aggregate shifted data
            x = np.concatenate([freqs_hz * aT_i for aT_i in aT])
            y = np.concatenate([storages[i] for i in range(n_temps)])
            # prepare data: sort and remove non-positive
            order = np.argsort(x)
            xs = x[order]
            ys = y[order]
            mask = (xs > 0) & (ys > 0)
            xs = xs[mask]
            ys = ys[mask]
            # aggregate duplicate frequencies by averaging
            ux, inv = np.unique(xs, return_inverse=True)
            uy = np.array([ys[inv == i].mean() for i in range(len(ux))])
            # choose interpolation kind: need at least 4 points for cubic
            ip_kind = 'cubic' if len(ux) >= 4 else 'linear'
            # create interpolation in log-log space
            interp_fn = interp1d(np.log10(ux), np.log10(uy), kind=ip_kind, fill_value='extrapolate')
            xlog_min = -1
            xlog_max = np.max(np.log10(ux))
            x_log = np.linspace(xlog_min, xlog_max, 200)
            y_log = interp_fn(x_log)
            x_plot = 10 ** x_log
            y_plot = 10 ** y_log
            orig_min = x.min()
            # collect for combined plot
            combined_curves[key] = (x_plot, y_plot, orig_min)
            # plot master curve line
            plt.plot(x_plot, y_plot, label=f'{key} master')
            # distinguish extrapolated region (< min original shifted freq)
            mask_extrap = x_plot < orig_min
            plt.scatter(x_plot[mask_extrap], y_plot[mask_extrap], color='red', marker='x', s=20, label=f'{key} extrapolated' if key=='WLF1' else None)
            # configure plot appearance
            plt.xscale('log')
            plt.yscale('log')
            plt.xlabel(f'Frequency (Hz) shifted to reference temperature ({reference_temp} K)')
            plt.ylabel('Storage Modulus (MPa)')
            plt.title(f'{key} Master Curve (WLF C1={C1}, C2={C2})')
            plt.legend()
            plt.tight_layout()
            plots[key] = f'{key}_master_curve.png'
            plt.savefig(os.path.join(cwd, plots[key]))
            plt.clf()
        # plot combined master curves
        fig2, ax2 = plt.subplots(figsize=(6,4))
        for key, (x_plot, y_plot, orig_min) in combined_curves.items():
            ax2.loglog(x_plot, y_plot, label=f'{key} master')
            if key == 'WLF1':
                mask_ex = x_plot < orig_min
                ax2.scatter(x_plot[mask_ex], y_plot[mask_ex], color='red', marker='x', s=20, label=f'{key} extrapolated')
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.set_xlabel(f'Frequency (Hz) shifted to reference temperature ({reference_temp} K)')
        ax2.set_ylabel('Storage Modulus (MPa)')
        ax2.set_title('Combined Master Curve (WLF Shifts)')
        ax2.legend()
        fig2.tight_layout()
        master_plot = os.path.join(cwd, 'master_curve_combined.png')
        fig2.savefig(master_plot)
        plt.close(fig2)
        # return all plots
        return Response(
            output=DmaxMasterCurveFlowDocument(
                temperatures=temperatures,
                freqs_ghz=freqs_ghz,
                data_csv=csv_file,
                master_plot_wlf1=os.path.join(cwd, plots['WLF1']),
                master_plot_wlf2=os.path.join(cwd, plots['WLF2']),
            )
        )
