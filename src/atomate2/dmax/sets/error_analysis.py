"""
LAMMPS InputSet for runtime and error analysis simulations.
"""

from pymatgen.io.lammps.generators import BaseLammpsSetGenerator


class ErrorAnalysisSet(BaseLammpsSetGenerator):
    """
    InputSet generating an in.lammps template for error analysis.
    Uses the 'in.master_error_analysis' template.

    Parameters
    ----------
    temperature : float
        Simulation temperature in K.
    nsteps : int
        Number of MD steps.
    timestep : float
        Time step in ps.
    tolerance : float
        Convergence tolerance for error evaluation.
    """

    def __init__(
        self,
        temperature: float = 300.0,
        nsteps: int = 50000,
        timestep: float = 1.0,
        tolerance: float = 1e-5,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template = "in.master_error_analysis"
        self.settings.update(
            {
                "temperature": temperature,
                "nsteps": nsteps,
                "timestep": timestep,
                "tolerance": tolerance,
            }
        )
