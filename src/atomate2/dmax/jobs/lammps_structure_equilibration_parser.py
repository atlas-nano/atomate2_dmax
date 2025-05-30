import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass
from jobflow import Maker, job, Response

# import MDAnalysis modules
import MDAnalysis as mda
from MDAnalysis.analysis.msd import EinsteinMSD
from MDAnalysis.analysis.vacf import VACF
from MDAnalysis.analysis.rdf import InterRDF

from atomate2.dmax.schemas.task import (
    DmaxStructureEquilParserDocument,
    DmaxStructureEquilitationFlowDocument,
)

@dataclass
class StructureEquilParserMaker(Maker):
    """
    Parser maker for structure equilibration flow. Reads LAMMPS logs and trajectories,
    generates plots, and returns a parser document.
    """
    name: str = "structure_equilibration_parser"

    @job(output_schema=DmaxStructureEquilParserDocument)
    def make(self, flow_doc: DmaxStructureEquilitationFlowDocument) -> Response:
        # Determine directories and file paths
        input_dir = str(flow_doc.input_dir)
        # find log file (any .log in input_dir)
        log_files = glob.glob(os.path.join(input_dir, '*.log'))
        log_file = log_files[0] if log_files else None
        # restart file
        restart_file = str(flow_doc.restart_file) if flow_doc.restart_file else None

        # Parse thermo data
        thermo_cols = ['step','dt','time','etotal','ecouple','ke','pe','temp','press',
                       'pxx','pyy','pzz','pxy','pxz','pyz','lx','ly','lz','vol','density']
        thermo_data = []
        if log_file:
            with open(log_file) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == len(thermo_cols):
                        try:
                            values = [float(x) for x in parts]
                            thermo_data.append(values)
                        except ValueError:
                            continue
        df = pd.DataFrame(thermo_data, columns=thermo_cols) if thermo_data else None

        plots = {}
        # Plot each property vs time
        if df is not None:
            for col in ['etotal','ecouple','press','temp','density']:
                plt.figure()
                plt.plot(df['time'], df[col])
                plt.xlabel('time')
                plt.ylabel(col)
                fname = f"{col}.png"
                outpath = os.path.join(input_dir, fname)
                plt.savefig(outpath)
                plt.close()
                plots[f'{col}_plot'] = outpath

        # Parse trajectories for MSD, VACF, RDF
        traj_files = glob.glob(os.path.join(input_dir, '*.lammpstrj'))
        if traj_files:
            # use first trajectory for analysis
            u = mda.Universe(traj_files[0])
            # MSD
            msd_an = EinsteinMSD(u).run()
            plt.figure()
            plt.plot(msd_an.times, msd_an.results.timeseries)
            msd_file = os.path.join(input_dir, 'msd.png')
            plt.savefig(msd_file)
            plt.close()
            plots['msd_plot'] = msd_file

            # VACF
            vacf_an = VACF(u, u.atoms).run()
            plt.figure()
            plt.plot(vacf_an.times, vacf_an.results['vacf'])
            vacf_file = os.path.join(input_dir, 'vacf.png')
            plt.savefig(vacf_file)
            plt.close()
            plots['vacf_plot'] = vacf_file

            # RDF
            rdf_an = InterRDF(u.select_atoms('all'), u.select_atoms('all'), nbins=75).run()
            plt.figure()
            plt.plot(rdf_an.bins, rdf_an.rdf)
            rdf_file = os.path.join(input_dir, 'rdf.png')
            plt.savefig(rdf_file)
            plt.close()
            plots['rdf_plot'] = rdf_file

        # build output document
        output = DmaxStructureEquilParserDocument(
            input_dir=input_dir,
            log_file=log_file,
            restart_file=restart_file,
            etotal_plot=plots.get('etotal_plot'),
            ecouple_plot=plots.get('ecouple_plot'),
            press_plot=plots.get('press_plot'),
            temp_plot=plots.get('temp_plot'),
            density_plot=plots.get('density_plot'),
            msd_plot=plots.get('msd_plot'),
            vacf_plot=plots.get('vacf_plot'),
            rdf_plot=plots.get('rdf_plot'),
        )
        return Response(output=output)
