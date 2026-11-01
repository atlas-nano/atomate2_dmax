"""
LAMMPS InputSet for polymer structure equilibration.
"""

from pymatgen.io.lammps.generators import BaseLammpsSetGenerator


class StructureEquilibrationSet(BaseLammpsSetGenerator):
    """
    InputSet generating an in.lammps for structure equilibration of a polymer.
    Uses the `in.master_structure_equilibration` template.

    Parameters
    ----------
    temperature : float
        Target temperature in K.
    pressure : float
        Target pressure in bar.
    nsteps : int
        Number of MD steps.
    timestep : float
        Time step in ps.
    """

    def __init__(
        self,
        system_name: str = "system",
        temperature: float = 300.0,
        pressure: float = 1.0,
        heat_steps: int = 10000,
        npt_steps: int = 1000000,
        prod_steps: int = 1000000,
        units: str = "real",
        atom_style: str = "full",
        boundary: str = "p p p",
        dielectric: float = 1.0,
        special_bonds: str = "0.0 0.0 0.5",
        pair_style: str = "lj/cut/coul/long 10",
        bond_style: str = "harmonic",
        angle_style: str = "harmonic",
        dihedral_style: str = "opls",
        improper_style: str = "none",
        kspace_style: str = "pppm 1e-06",
        data_file: str = "data.master",
        pair_modify: str = "mix geometric",
        neighbor: str = "2.0 bin",
        neigh_modify: str = "every 2 delay 4 check yes one 3000",
        thermo_style: str = (
            "custom step dt time etotal ecouple ke temp pe press pxx pyy pzz pxy pxz pyz lx ly lz vol density"
        ),
        timestep: float = 1.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template = "in.master_structure_equilibration"
        # populate template variables
        self.settings.update(
            {
                "system_name": system_name,
                "temperature": temperature,
                "pressure": pressure,
                "heat_steps": heat_steps,
                "npt_steps": npt_steps,
                "prod_steps": prod_steps,
                # LAMMPS settings
                "units": units,
                "atom_style": atom_style,
                "boundary": boundary,
                "dielectric": dielectric,
                "special_bonds": special_bonds,
                "pair_style": pair_style,
                "bond_style": bond_style,
                "angle_style": angle_style,
                "dihedral_style": dihedral_style,
                "improper_style": improper_style,
                "kspace_style": kspace_style,
                "data_file": data_file,
                "pair_modify": pair_modify,
                "neighbor": neighbor,
                "neigh_modify": neigh_modify,
                "thermo_style": thermo_style,
                "timestep": timestep,
            }
        )
