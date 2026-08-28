"""
DMAx-specific settings that extend the base Atomate2Settings.

This module provides additional configuration options for DMAx workflows
that are not part of the base atomate2 settings.
"""

from __future__ import annotations

from pydantic import Field

from atomate2.settings import Atomate2Settings


class DmaxSettings(Atomate2Settings):
    """
    Settings for DMAx workflows extending base Atomate2Settings.

    This class adds DMAx-specific configuration options while maintaining
    compatibility with the base atomate2 settings system.
    """

    # LAMMPS-specific settings
    LAMMPS_RUN_COMMAND: str = Field(
        default="lmp_serial", description="Command to run LAMMPS simulations"
    )

    # Data storage settings
    STORE_VOLUMETRIC_DATA: bool = Field(
        default=True, description="Whether to store volumetric data from simulations"
    )

    STORE_TRAJECTORY: bool = Field(
        default=True, description="Whether to store MD trajectories"
    )

    # LAMMPS computational settings
    LAMMPS_INCAR_UPDATES: dict = Field(
        default_factory=dict, description="Updates to apply to LAMMPS input files"
    )

    LAMMPS_KSPACING: float = Field(
        default=0.5, description="K-point spacing for LAMMPS calculations"
    )

    # Force field settings
    DEFAULT_FF_METHOD: str = Field(
        default="ligpargen",
        description="Default force field parameterization method (ligpargen, foyer)",
    )

    DEFAULT_FF_NAME: str = Field(
        default="oplsaa", description="Default force field name (oplsaa, gaff2, etc.)"
    )

    # GPU settings
    USE_GPU: bool = Field(
        default=False, description="Whether to use GPU acceleration for LAMMPS"
    )

    GPU_COUNT: int = Field(
        default=1, description="Number of GPUs to use for LAMMPS calculations"
    )


# Create a global instance for use throughout DMAx
try:
    DMAX_SETTINGS = DmaxSettings()
except Exception as e:
    # Fallback to base settings if DMAx settings fail
    import warnings

    warnings.warn(
        f"Failed to load DMAx settings ({e}), falling back to base Atomate2Settings. "
        "Some DMAx-specific features may not work correctly.",
        UserWarning,
    )
    DMAX_SETTINGS = Atomate2Settings()
