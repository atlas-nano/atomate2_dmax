"""
LAMMPS InputSet for dynamic mechanical analysis (DMA) of polymers.
"""

from pymatgen.io.lammps.generators import BaseLammpsSetGenerator


class DynamicMechanicalSet(BaseLammpsSetGenerator):
    """
    InputSet for dynamic mechanical analysis simulations.
    Uses the 'in.master_dynamic_mechanical_analysis' template.

    Parameters
    ----------
    temperature : float
        Simulation temperature in K.
    frequency : float
        Oscillation frequency in Hz.
    amplitude : float
        Oscillation amplitude (strain) in decimal.
    ncycles : int
        Number of oscillation cycles.
    nsteps_per_cycle : int
        Number of MD steps per cycle.
    timestep : float
        Time step in ps.
    """

    def __init__(
        self,
        temperature: float = 300.0,
        frequency: float = 1.0,
        amplitude: float = 0.01,
        ncycles: int = 10,
        nsteps_per_cycle: int = 1000,
        timestep: float = 1.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template = "in.master_dynamic_mechanical_analysis"
        # total steps = ncycles * nsteps_per_cycle
        total_steps = ncycles * nsteps_per_cycle
        self.settings.update(
            {
                "temperature": temperature,
                "frequency": frequency,
                "amplitude": amplitude,
                "ncycles": ncycles,
                "nsteps_per_cycle": nsteps_per_cycle,
                "nsteps": total_steps,
                "timestep": timestep,
            }
        )
