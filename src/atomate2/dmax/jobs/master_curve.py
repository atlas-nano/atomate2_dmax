# ─── imports ──────────────────────────────────────────────────────────────────
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from jobflow import Maker, Response, job

# same location that every other file imports it from
from atomate2.dmax.schemas.task import DmaxDmaParserDocument

# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class MasterCurvePlotMaker(Maker):
    """Build a storage-modulus master-curve (GPa vs frequency) from the list of
    parsed DMA documents produced by ``MasterCurveFlow``.

    *One* parser document is produced for every (temperature, frequency)
    combination, so we expect:

        ``len(docs) == n_temps * n_freqs``

    Parameters
    ----------
    freqs_GHz
        Frequencies probed at each temperature **in the same order** in which the
        DMA jobs were run.
    temps_K
        Temperatures (K) that were swept.
    reference_temp_K
        If given, this curve will be highlighted in the legend.
    save_path
        Where to write the PNG file (relative paths are resolved against CWD).
    """

    freqs_GHz: Sequence[float]
    temps_K: Sequence[float]

    reference_temp_K: float | None = None
    save_path: str | Path = "master_curve.png"

    name: str = field(default="master_curve_plot", init=False)

    # ────────────────────────────────────────────────────────────────────────
    @job
    def make(
        self,
        dma_docs: Sequence[DmaxDmaParserDocument],
    ) -> Response:
        # unpack dimensions
        n_temps = len(self.temps_K)
        n_freqs = len(self.freqs_GHz)
        if len(dma_docs) != n_temps * n_freqs:
            raise ValueError(
                f"Expected {n_temps * n_freqs} docs but got {len(dma_docs)}."
            )
        # prepare data matrices (GPa or dimensionless for tan_delta)
        stor_mod = np.zeros((n_temps, n_freqs))
        loss_mod = np.zeros((n_temps, n_freqs))
        tan_delta = np.zeros((n_temps, n_freqs))
        # fill matrices and convert units
        idx = 0
        for i_t, T in enumerate(self.temps_K):
            for i_f, f in enumerate(self.freqs_GHz):
                doc = dma_docs[idx]
                stor_mod[i_t, i_f] = max(doc.storage_modulus, 1e-3)  # MPa
                loss_mod[i_t, i_f] = max(doc.loss_modulus, 1e-3)  # MPa
                tan_delta[i_t, i_f] = (
                    doc.loss_modulus and doc.loss_modulus / doc.storage_modulus
                )
                idx += 1
        # convert frequencies to Hz
        freq_Hz = np.array(self.freqs_GHz) * 1e9
        # determine reference temperature
        T_ref = (
            self.reference_temp_K
            if self.reference_temp_K is not None
            else self.temps_K[n_temps // 2]
        )
        # WLF parameter sets
        wlf_params = {"WLF1": (17.44, 51.6), "WLF2": (8.86, 101.6)}
        # output file base
        base = Path(self.save_path).stem
        out_dir = Path(self.save_path).expanduser().resolve().parent
        out_dir.mkdir(parents=True, exist_ok=True)
        # 1. Raw plots: storage, loss, tan_delta vs frequency
        for mat, ylabel, suffix in [
            (stor_mod, "Storage modulus (GPa)", "storage_raw"),
            (loss_mod, "Loss modulus (MPa)", "loss_raw"),
            (tan_delta, "Loss tangent", "tan_delta_raw"),
        ]:
            fig, ax = plt.subplots(figsize=(6, 4))
            for i, T in enumerate(self.temps_K):
                # connect points with lines and markers
                ax.plot(freq_Hz, mat[i], marker="x", linestyle="-", label=f"{T:.0f} K")
            # adjust font sizes and ticks
            ax.tick_params(axis="both", which="major", labelsize=8)
            ax.set_xscale("log")  # log scale on x-axis only
            ax.set_xlabel("Frequency (Hz)", fontsize=10)
            ax.set_ylabel(ylabel, fontsize=10)
            ax.set_title(f"{ylabel} vs frequency", fontsize=12)
            ax.grid(True, which="both", ls=":", lw=0.4)
            ax.legend(fontsize="small")
            fig.tight_layout(pad=1.0)
            fig.savefig(out_dir / (f"{base}_{suffix}.png"), dpi=300)
            plt.close(fig)
        # 2. WLF mastercurve plots for each param set and material
        for name, (C1, C2) in wlf_params.items():
            # compute shift factors for each temperature
            loga = [(C1 * (T - T_ref) / (C2 + (T - T_ref))) for T in self.temps_K]
            a_facs = 10 ** np.array(loga)
            # apply shifts and plot each property
            for mat, ylabel, suffix in [
                (stor_mod, "Storage modulus (GPa)", "storage"),
                (loss_mod, "Loss modulus (MPa)", "loss"),
                (tan_delta, "Loss tangent", "tan_delta"),
            ]:
                # shifted frequencies
                fsh = (freq_Hz[None, :] * a_facs[:, None]).ravel()
                ysh = mat.ravel()
                # sort for continuous line
                fig, ax = plt.subplots(figsize=(6, 4))
                # adjust font sizes and ticks
                ax.tick_params(axis="both", which="major", labelsize=8)
                fig.tight_layout(pad=1.0)  # ensure labels and title fit
                # scatter data points
                ax.scatter(fsh, ysh, s=10, alpha=0.6, label="shifted data")
                # log scale on x-axis for mastercurve
                ax.set_xscale("log")
                ax.set_xlabel("Reduced frequency (Hz)")
                ax.set_ylabel(ylabel)
                ax.set_title(f"{ylabel} master curve ({name})")
                ax.grid(True, which="both", ls=":", lw=0.4)
                ax.legend(fontsize="small")
                fig.savefig(out_dir / (f"{base}_{suffix}_{name}.png"), dpi=300)
                plt.close(fig)
        return Response(output=str(self.save_path))
