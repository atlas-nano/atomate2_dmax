import os
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response

from atomate2.dmax.schemas.task import DmaxErrorAnalysisFlowDocument
from atomate2.dmax.schemas.task import DmaxDmaParserDocument

@dataclass
class ErrorAnalysisPlotMaker(Maker):
    """Maker to plot error analysis metrics across frequencies"""
    name: str = 'error_analysis_plot'

    @job(output_schema=DmaxErrorAnalysisFlowDocument)
    def make(self, parser_groups: list[list[DmaxDmaParserDocument]], freqs_ghz: list[float]) -> Response:
        # compute stats for each frequency
        storage_mean = []
        storage_std = []
        loss_mean = []
        loss_std = []
        tan_mean = []
        tan_std = []
        for docs in parser_groups:
            storages = [d.storage_modulus for d in docs]
            losses = [d.loss_modulus for d in docs]
            tans = [d.tan_delta or 0.0 for d in docs]
            storage_mean.append(float(np.mean(storages)))
            storage_std.append(float(np.std(storages)))
            loss_mean.append(float(np.mean(losses)))
            loss_std.append(float(np.std(losses)))
            tan_mean.append(float(np.mean(tans)))
            tan_std.append(float(np.std(tans)))
        # plotting
        cwd = os.getcwd()
        storage_plot = os.path.join(cwd, 'storage_vs_freq.png')
        plt.figure()
        plt.errorbar(freqs_ghz, storage_mean, yerr=storage_std, fmt='o-', capsize=5)
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Storage Modulus (MPa)')
        plt.tight_layout()
        plt.savefig(storage_plot)
        plt.close()
        
        loss_plot = os.path.join(cwd, 'loss_vs_freq.png')
        plt.figure()
        plt.errorbar(freqs_ghz, loss_mean, yerr=loss_std, fmt='s-', capsize=5)
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Loss Modulus (MPa)')
        plt.tight_layout()
        plt.savefig(loss_plot)
        plt.close()
        
        tan_plot = os.path.join(cwd, 'tan_delta_vs_freq.png')
        plt.figure()
        plt.errorbar(freqs_ghz, tan_mean, yerr=tan_std, fmt='d-', capsize=5)
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Loss Tangent (tan δ)')
        plt.tight_layout()
        plt.savefig(tan_plot)
        plt.close()
        
        return Response(
            output=DmaxErrorAnalysisFlowDocument(
                freqs_ghz=freqs_ghz,
                storage_mean=storage_mean,
                storage_std=storage_std,
                loss_mean=loss_mean,
                loss_std=loss_std,
                tan_mean=tan_mean,
                tan_std=tan_std,
                storage_plot=storage_plot,
                loss_plot=loss_plot,
                tan_plot=tan_plot,
            )
        )
