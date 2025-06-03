import os
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response
from scipy.interpolate import UnivariateSpline
import csv

from atomate2.dmax.schemas.task import DmaxGlassTransitionFlowDocument
from atomate2.dmax.schemas.task import DmaxDmaParserDocument

@dataclass
class GlassTransitionPlotMaker(Maker):
    """Maker to plot SM, LM, and tanδ vs temperature and estimate Tg"""
    name: str = 'glass_transition_plot'

    @job(output_schema=DmaxGlassTransitionFlowDocument)
    def make(self, parser_docs: list[DmaxDmaParserDocument], temperatures: list[float]) -> Response:
        # extract metrics
        storages = np.array([d.storage_modulus for d in parser_docs], dtype=float)
        losses = np.array([d.loss_modulus for d in parser_docs], dtype=float)
        tans = np.array([d.tan_delta if d.tan_delta is not None else np.nan for d in parser_docs], dtype=float)
        temps = np.array(temperatures, dtype=float)
        # fit smoothing spline to tan_delta vs T
        try:
            spline = UnivariateSpline(temps, tans, k=4, s=0)
            d2 = spline.derivative(n=2)
            Ts = np.linspace(temps.min(), temps.max(), 500)
            vals = d2(Ts)
            # find sign changes for inflection
            roots = []
            for i in range(len(Ts)-1):
                if vals[i] == 0 or vals[i] * vals[i+1] < 0:
                    # linear interpolation root
                    root = Ts[i] - vals[i] * (Ts[i+1]-Ts[i])/(vals[i+1]-vals[i])
                    roots.append(root)
            glass_temp = float(roots[0]) if roots else float(np.nan)
        except Exception:
            glass_temp = float(np.nan)
        # prepare additional metrics for CSV
        elastics = np.array([d.elastic_modulus for d in parser_docs], dtype=float)
        poissons = np.array([d.poisson_ratio for d in parser_docs], dtype=float)
        # write data CSV
        cwd = os.getcwd()
        data_csv = os.path.join(cwd, 'glass_transition_data.csv')
        # write CSV without pandas
        with open(data_csv, 'w', newline='') as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow(['temperature', 'storage_modulus', 'loss_modulus', 'tan_delta', 'elastic_modulus', 'poisson_ratio'])
            for T, sm, lm, td, em, pr in zip(temps, storages, losses, tans, elastics, poissons):
                writer.writerow([T, sm, lm, td, em, pr])
        # plot curves with dual-axis
        plot_file = os.path.join(cwd, 'glass_transition.png')
        fig, ax1 = plt.subplots()
        # plot storage and loss moduli on left axis
        ax1.scatter(temps, storages, color='tab:blue', alpha=0.4)
        ax1.plot(temps, storages, color='tab:blue', linestyle='-', label='Storage Modulus')
        ax1.scatter(temps, losses, color='tab:orange', alpha=0.4)
        ax1.plot(temps, losses, color='tab:orange', linestyle='-', label='Loss Modulus')
        ax1.set_xlabel('Temperature (K)')
        ax1.set_ylabel('Modulus', color='k')
        ax1.tick_params(axis='y', labelcolor='k')
        # plot tan delta on right axis
        ax2 = ax1.twinx()
        ax2.scatter(temps, tans, color='tab:green', alpha=0.4)
        ax2.plot(temps, tans, color='tab:green', linestyle='-', label='Loss Tangent')
        ax2.set_ylabel('Tan δ', color='tab:green')
        ax2.tick_params(axis='y', labelcolor='tab:green')
        # combine legends
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='best')
        # annotate Tg
        if not np.isnan(glass_temp):
            ax1.axvline(glass_temp, color='r', linestyle='--')
            ax1.text(0.05, 0.95, f'Tg = {glass_temp:.1f} K', transform=ax1.transAxes,
                     verticalalignment='top', bbox=dict(facecolor='white', alpha=0.6))
        fig.tight_layout()
        fig.savefig(plot_file)
        plt.close(fig)
        return Response(
            output=DmaxGlassTransitionFlowDocument(
                temperatures=temperatures,
                storage_modulus=storages.tolist(),
                loss_modulus=losses.tolist(),
                tan_delta=tans.tolist(),
                glass_transition_temp=glass_temp,
                plot=plot_file,
                data_csv=data_csv,
            )
        )
