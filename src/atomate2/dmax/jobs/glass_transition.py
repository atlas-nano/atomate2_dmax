import os
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response
from scipy.interpolate import UnivariateSpline

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
        # plot curves
        cwd = os.getcwd()
        plot_file = os.path.join(cwd, 'glass_transition.png')
        plt.figure()
        # storage modulus
        plt.scatter(temps, storages, color='tab:blue', alpha=0.4)
        plt.plot(temps, storages, color='tab:blue', linestyle='-', label='Storage Modulus')
        # loss modulus
        plt.scatter(temps, losses, color='tab:orange', alpha=0.4)
        plt.plot(temps, losses, color='tab:orange', linestyle='-', label='Loss Modulus')
        # tan delta
        plt.scatter(temps, tans, color='tab:green', alpha=0.4)
        plt.plot(temps, tans, color='tab:green', linestyle='-', label='Loss Tangent')
        plt.xlabel('Temperature (K)')
        plt.ylabel('Modulus / Tan δ')
        plt.legend()
        # annotate Tg
        if not np.isnan(glass_temp):
            plt.axvline(glass_temp, color='r', linestyle='--', label=f'Tg = {glass_temp:.1f} K')
            # text box
            plt.text(0.05, 0.95, f'Tg = {glass_temp:.1f} K', transform=plt.gca().transAxes,
                     verticalalignment='top', bbox=dict(facecolor='white', alpha=0.6))
        plt.tight_layout()
        plt.savefig(plot_file)
        plt.close()
        return Response(
            output=DmaxGlassTransitionFlowDocument(
                temperatures=temperatures,
                storage_modulus=storages.tolist(),
                loss_modulus=losses.tolist(),
                tan_delta=tans.tolist(),
                glass_transition_temp=glass_temp,
                plot=plot_file,
            )
        )
