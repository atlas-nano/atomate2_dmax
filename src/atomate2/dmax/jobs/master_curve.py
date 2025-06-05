# ─── imports ──────────────────────────────────────────────────────────────────
from __future__ import annotations

from pathlib import Path
from typing   import Sequence, Optional

import matplotlib.pyplot as plt
import numpy as np
from jobflow import Maker, Response, job
from dataclasses import dataclass, field

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
    temps_K:   Sequence[float]
    
    reference_temp_K: Optional[float] = None
    save_path: str | Path = "master_curve.png"

    name: str = field(default="master_curve_plot", init=False)

    # ────────────────────────────────────────────────────────────────────────
    @job
    def make(self,
             dma_docs: Sequence[DmaxDmaParserDocument],
             ) -> Response:

        n_temps = len(self.temps_K)
        n_freqs = len(self.freqs_GHz)

        if len(dma_docs) != n_temps * n_freqs:
            raise ValueError(
                f"Expected {n_temps*n_freqs} parser docs "
                f"({n_temps} temps × {n_freqs} freqs) but got {len(dma_docs)}."
            )

        # ------------------------------------------------------------------
        # reshape flat list → (temps, freqs) matrix of storage-modulus values
        # ------------------------------------------------------------------
        stor_mod_GPa = np.empty((n_temps, n_freqs))

        idx = 0
        for i_t in range(n_temps):
            for i_f in range(n_freqs):
                # convert MPa → GPa, enforce strictly positive values
                mp = max(dma_docs[idx].storage_modulus, 1e-3)           # MPa
                stor_mod_GPa[i_t, i_f] = mp / 1000.0                    # GPa
                idx += 1

        # ──────────────────────────────────────────────────────────────────
        # plotting
        # ──────────────────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(6, 4))

        for t_idx, T in enumerate(self.temps_K):
            label = f"{T:.0f} K"
            if self.reference_temp_K is not None and np.isclose(T, self.reference_temp_K):
                label += "  (reference)"

            y = stor_mod_GPa[t_idx]
            # protect against matplotlib’s “no positive values” error
            y = np.where(y <= 0, 1e-6, y)

            ax.semilogx(self.freqs_GHz, y, marker="o", label=label)

        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Storage modulus (GPa)")
        ax.set_title("DMA master curve")
        ax.grid(True, which="both", ls=":", lw=0.4)
        ax.legend(fontsize="small")
        plt.tight_layout()

        save_path = Path(self.save_path).expanduser().resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=300)
        plt.close(fig)

        return Response(output=str(save_path))
