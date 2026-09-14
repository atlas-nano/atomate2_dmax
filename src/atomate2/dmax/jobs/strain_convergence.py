import os
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from jobflow import Maker, Response, job

from atomate2.dmax.schemas.task import (
    DmaxDmaParserDocument,
    DmaxStrainSizeConvergenceFlowDocument,
)


@dataclass
class StrainConvergencePlotMaker(Maker):
    """Maker to plot convergence metrics and select optimal oscillation amplitude"""

    name: str = "strain_convergence_plot"

    @job(output_schema=DmaxStrainSizeConvergenceFlowDocument)
    def make(
        self,
        parser_docs: list[DmaxDmaParserDocument],
        amps: list[float],
        restart_files: list[Any],
    ) -> Response:
        # extract metrics
        rmse_vals = [doc.fit_rmse for doc in parser_docs]
        r2_vals = [doc.fit_r2 for doc in parser_docs]
        # plot RMSE and R2 vs amplitude
        plot_file = os.path.join(os.getcwd(), "dma_convergence.png")
        fig, ax1 = plt.subplots()
        ax1.plot(amps, rmse_vals, "r-o", label="RMSE")
        ax1.set_xlabel("Oscillation amplitude (%)")
        ax1.set_ylabel("RMSE (MPa)", color="r")
        ax1.tick_params(axis="y", labelcolor="r")
        ax2 = ax1.twinx()
        ax2.plot(amps, r2_vals, "b-s", label="R²")
        ax2.set_ylabel("R²", color="b")
        ax2.tick_params(axis="y", labelcolor="b")
        fig.tight_layout()
        fig.savefig(plot_file)
        plt.close(fig)
        # compute Poisson's ratio data
        poisson_vals = [doc.poisson_ratio for doc in parser_docs]
        poisson_plot_file = os.path.join(os.getcwd(), "poisson_ratio_vs_amp.png")
        fig2, axp = plt.subplots()
        axp.plot(amps, poisson_vals, "g-^", label="Poisson's ratio")
        axp.set_xlabel("Oscillation amplitude (%)")
        axp.set_ylabel("Poisson's ratio")
        fig2.tight_layout()
        fig2.savefig(poisson_plot_file)
        plt.close(fig2)
        # rank and select optimal amplitude
        rmse_rank = np.argsort(rmse_vals)
        r2_rank = np.argsort([-v for v in r2_vals])
        combined = rmse_rank + r2_rank
        opt_idx = int(np.argmin(combined))
        optimal_amp = float(amps[opt_idx])
        # restart.equil path that belongs to the optimal amplitude
        optimal_restart = str(restart_files[opt_idx])
        print(f"Optimal restart file: {optimal_restart}")
        # -------------------------------------------------------------- #
        # Build downstream flow (lazy import avoids circular import)
        # -------------------------------------------------------------- #
        # -------------------------------------------------------------- #
        # Detour: launch NumCyclesConvergenceFlow on the *same directory*
        # -------------------------------------------------------------- #
        from atomate2.dmax.flows.core import NumCyclesConvergenceFlow

        detour_flow = NumCyclesConvergenceFlow(
            threshold=0.01  # or expose as attribute
        ).make(optimal_restart)
        cycle_job = detour_flow.jobs[-1]

        return Response(
            output=DmaxStrainSizeConvergenceFlowDocument(
                osc_amp_pc=amps,  # list you tested
                rmse=rmse_vals,
                r2=r2_vals,
                plot=plot_file,
                poisson=poisson_vals,
                poisson_plot=poisson_plot_file,
                optimal_osc_amp_pc=optimal_amp,
                optimal_work_dir=os.path.dirname(optimal_restart),
                optimal_restart_file=optimal_restart,
                optimal_num_cycles=cycle_job.output.optimal_num_cycles,
            ),
            detour=detour_flow,
        )
