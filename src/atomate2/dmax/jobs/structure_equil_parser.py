import os
import glob
import importlib
import pandas as pd
import matplotlib.pyplot as plt
from jobflow import Maker, job, Response
from dataclasses import dataclass

from atomate2.dmax.schemas.task import (
    DmaxStructureEquilParserDocument,
    DmaxLammpsInputDocument,
    DmaxLammpsRunDocument,
)

@dataclass
class StructureEquilParserMaker(Maker):
    """
    Maker to parse outputs from structure equilibration: thermo, MSD, VACF, RDF, and restart.
    """
    name: str = "structure_equil_parser"

    @job(output_schema=DmaxStructureEquilParserDocument)
    def make(
        self,
        input_doc: DmaxLammpsInputDocument,
        run_doc: DmaxLammpsRunDocument,
    ) -> Response:
        wd = input_doc.input_dir
        # find LAMMPS log file
        logs = [f for f in os.listdir(wd) if f.endswith('.log')]
        log_file = None
        for f in logs:
            with open(os.path.join(wd, f), 'r') as fh:
                if 'LAMMPS' in fh.readline():
                    log_file = f
                    break
        if not log_file:
            raise FileNotFoundError("LAMMPS log file not found in " + wd)
        log_path = os.path.join(wd, log_file)
        # find LAMMPS input script and extract thermo_style labels
        input_script = os.path.join(wd, input_doc.input_file)
        labels = None
        with open(input_script, 'r') as f_in:
            for line in f_in:
                parts = line.strip().split()
                if parts and parts[0] == 'thermo_style':
                    # parts: ['thermo_style', 'custom', 'step', 'dt', ...] or without 'custom'
                    if len(parts) > 1 and parts[1] == 'custom':
                        labels = parts[2:]
                    else:
                        labels = parts[1:]
                    break
        # parse thermo data from log using labels from input script
        data = []
        if labels is None:
            raise RuntimeError(f"Could not find thermo_style in input script {input_script}")
        with open(log_path, 'r') as fh:
            for line in fh:
                stripped = line.strip()
                if stripped and stripped[0].isdigit():
                    vals = stripped.split()
                    if len(vals) == len(labels):
                        data.append(vals)
        if not data:
            raise RuntimeError(f"No thermo data lines found in log {log_path} for labels {labels}")
        df = pd.DataFrame(data, columns=labels).astype(float)
        # save thermo CSV
        thermo_csv = os.path.join(wd, 'thermo.csv')
        df.to_csv(thermo_csv, index=False)
        # plot thermo properties
        plot_paths = {}
        specs = {
            'etotal': 'Total Energy',
            'ecouple': 'Thermostat Energy',
            'press': 'Pressure',
            'temp': 'Temperature',
            'density': 'Density',
        }
        # units for real units
        units_map = {
            'etotal': 'kcal/mol',
            'ecouple': 'kcal/mol',
            'press': 'atm',
            'temp': 'K',
            'density': 'g/cm^3',
        }
        for key, label in specs.items():
            if key in df.columns and 'time' in df.columns:
                times = df['time']
                values = df[key]
                # smoothing
                smoothed = values.rolling(window=5, min_periods=1, center=True).mean()
                plt.figure()
                plt.scatter(times, values, s=10, alpha=0.5, label='raw')
                plt.plot(times, smoothed, color='red', linewidth=2, label='trend')
                plt.xlabel('Time (fs)')
                plt.ylabel(f'{label} ({units_map[key]})')
                plt.title(f'{label} vs Time')
                plt.legend()
                plt.tight_layout()
                path = os.path.join(wd, f'{key}_vs_time.png')
                plt.savefig(path)
                plt.close()
                plot_paths[key] = path
        # trajectory analysis (use LAMMPS data + dump files)
        # Dynamically import MDAnalysis modules
        try:
            mda = importlib.import_module('MDAnalysis')
            msd_mod = importlib.import_module('MDAnalysis.analysis.msd')
            EinsteinMSD = getattr(msd_mod, 'EinsteinMSD')
        except ModuleNotFoundError:
            raise ImportError(
                "MDAnalysis and its msd module are required for structure equilibration parsing. "
                "Please install MDAnalysis (e.g., `pip install MDAnalysis`)."
            )
        # optional VACF
        try:
            vacf_mod = importlib.import_module('MDAnalysis.analysis.vacf')
            VACF = getattr(vacf_mod, 'VACF')
        except ModuleNotFoundError:
            VACF = None
        # optional RDF
        try:
            rdf_mod = importlib.import_module('MDAnalysis.analysis.rdf')
            InterRDF = getattr(rdf_mod, 'InterRDF')
        except ModuleNotFoundError:
            InterRDF = None
        data_file = os.path.join(wd, input_doc.data_file)
        dumps = glob.glob(os.path.join(wd, '*.lammpstrj'))
        if not dumps:
            raise FileNotFoundError("LAMMPS trajectory (.lammpstrj) not found")
        # load universe
        u = mda.Universe(data_file, dumps, topology_format='DATA', format='LAMMPSDUMP', dt=0.001)
        # MSD
        msd_analysis = EinsteinMSD(u, select='all', msd_type='xyz', unwrap=True)
        msd_analysis.run()
        # Extract MSD times and values
        try:
            msd_times = msd_analysis.results.time
        except Exception:
            msd_times = getattr(msd_analysis, 'times', None)
        try:
            msd_vals = msd_analysis.results.msd
        except Exception:
            results_dict = dict(msd_analysis.results)
            other_keys = [k for k in results_dict if k not in ('time', 'times')]
            if not other_keys:
                raise AttributeError("MSD values not found in results")
            msd_vals = results_dict[other_keys[0]]
        # plot average MSD with trend line
        plt.figure()
        # compute average across atoms if needed
        if hasattr(msd_vals, 'ndim') and msd_vals.ndim > 1:
            msd_avg = pd.DataFrame(msd_vals).mean(axis=1)
        else:
            msd_avg = pd.Series(msd_vals)
        plt.scatter(msd_times, msd_avg, s=10, alpha=0.5, label='raw')
        trend = msd_avg.rolling(window=5, min_periods=1, center=True).mean()
        plt.plot(msd_times, trend, color='red', linewidth=2, label='trend')
        plt.xlabel('Time (fs)')
        plt.ylabel('MSD (Å²)')
        plt.title('Mean Squared Displacement')
        plt.legend(loc='best', fontsize='small')
        plt.tight_layout()
        msd_plot = os.path.join(wd, 'msd.png')
        plt.savefig(msd_plot)
        plt.close()
        # VACF (if available)
        if VACF is not None:
            vacf_analysis = VACF(u, select='all')
            vacf_analysis.run()
            vacf_times = vacf_analysis.times
            vacf_vals = vacf_analysis.results.autocorrelation
            # plot VACF
            plt.figure()
            plt.scatter(vacf_times, vacf_vals, s=10, alpha=0.5, label='raw')
            trend = pd.Series(vacf_vals).rolling(window=5, min_periods=1, center=True).mean()
            plt.plot(vacf_times, trend, color='red', linewidth=2, label='trend')
            plt.xlabel('Time (fs)')
            plt.ylabel('VACF')
            plt.title('Velocity Autocorrelation Function')
            plt.legend()
            vacf_plot = os.path.join(wd, 'vacf.png')
            plt.savefig(vacf_plot)
            plt.close()
        else:
            vacf_plot = None
        # RDF (if available)
        if InterRDF is not None:
            atomgroup = u.select_atoms('all')
            rdf_analysis = InterRDF(atomgroup, atomgroup, nbins=75)
            rdf_analysis.run()
            bins = rdf_analysis.results.bins
            rdf_vals = rdf_analysis.results.rdf
            plt.figure()
            plt.scatter(bins, rdf_vals, s=10, alpha=0.5, label='rdf')
            plt.plot(bins, rdf_vals, color='blue', linewidth=2)
            plt.xlabel('Distance (Å)')
            plt.ylabel('g(r)')
            plt.title('Radial Distribution Function')
            plt.xlim(0, 5)
            plt.legend()
            rdf_plot = os.path.join(wd, 'rdf.png')
            plt.savefig(rdf_plot)
            plt.close()
        else:
            rdf_plot = None
        # assemble parser document
        return Response(
            output=DmaxStructureEquilParserDocument(
                restart_file=run_doc.restart_file,
                thermo_csv=thermo_csv,
                thermo_plot=plot_paths.get('etotal'),
                msd_plot=msd_plot,
                vacf_plot=vacf_plot,
                rdf_plot=rdf_plot,
            )
        )
