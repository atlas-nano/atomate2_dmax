"""
Wrapper module for PolymerStructurePredictor AmorphousBuilder.
"""

import os

import pandas as pd
from psp.AmorphousBuilder import Builder as PSPBuilder


class PSPBuilderWrapper:
    """
    Serializable wrapper for PSP AmorphousBuilder for jobflow.
    Stores minimal info to reconstruct builder and generate forcefields.
    """

    def __init__(
        self,
        out_dir: str,
        smiles: str,
        left_cap: str,
        right_cap: str,
        length: int,
        num_molecules: int,
        density: float,
        box_type: str,
        num_conf: int = 0,
        loop: bool = False,
    ):
        self.out_dir = out_dir
        self.smiles = smiles
        self.left_cap = left_cap
        self.right_cap = right_cap
        self.length = length
        self.num_molecules = num_molecules
        self.density = density
        self.box_type = box_type
        self.num_conf = num_conf
        self.loop = loop
        self._builder = None  # will hold the built PSPBuilder

    def get_builder(self):
        # if original builder stored, return it
        if hasattr(self, "_builder") and self._builder is not None:
            return self._builder
        # else reconstruct from stored parameters
        df = pd.DataFrame(
            [
                [
                    "polymer",
                    self.smiles,
                    self.left_cap,
                    self.right_cap,
                    self.length,
                    self.num_molecules,
                    self.num_conf,
                    self.loop,
                ]
            ],
            columns=[
                "ID",
                "smiles",
                "LeftCap",
                "RightCap",
                "Len",
                "Num",
                "NumConf",
                "Loop",
            ],
        )
        builder = PSPBuilder(
            df, density=self.density, box_type=self.box_type, OutDir=self.out_dir
        )
        return builder

    def as_dict(self):
        return {
            "out_dir": self.out_dir,
            "smiles": self.smiles,
            "left_cap": self.left_cap,
            "right_cap": self.right_cap,
            "length": self.length,
            "num_molecules": self.num_molecules,
            "density": self.density,
            "box_type": self.box_type,
            "num_conf": self.num_conf,
            "loop": self.loop,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def build_amorphous_structure(
    smiles: str,
    left_cap: str,
    right_cap: str,
    length: int,
    num_molecules: int,
    density: float,
    box_type: str,
    out_dir: str,
    num_conf: int = 1,
    loop: bool = False,
) -> PSPBuilderWrapper:
    """
    Generate an amorphous polymer structure using PSP AmorphousBuilder.

    Parameters
    ----------
    smiles
        SMILES of the repeating unit with attachment points ([*]).
    left_cap
        SMILES of the left cap group with attachment point.
    right_cap
        SMILES of the right cap group with attachment point.
    length
        Number of monomers per chain.
    num_molecules
        Number of polymer chains.
    density
        Initial packing density for builder.
    box_type
        Box type code for PSP (e.g., 'c' for cubic).
    out_dir
        Output directory for structure files.
    num_conf
        Number of initial conformers to generate (default 0).
    loop
        Whether to loop building until target density (default False).

    Returns
    -------
    PSPBuilderWrapper instance.
    """
    # prepare input DataFrame
    input_data = [
        [
            "polymer",
            smiles,
            left_cap,
            right_cap,
            length,
            num_molecules,
            num_conf,
            loop,
        ]
    ]
    columns = [
        "ID",
        "smiles",
        "LeftCap",
        "RightCap",
        "Len",
        "Num",
        "NumConf",
        "Loop",
    ]
    df = pd.DataFrame(input_data, columns=columns)

    # ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # run PSP builder
    builder = PSPBuilder(df, density=density, box_type=box_type, OutDir=out_dir)
    builder.Build()
    # wrap builder for reuse
    wrapper = PSPBuilderWrapper(
        out_dir=out_dir,
        smiles=smiles,
        left_cap=left_cap,
        right_cap=right_cap,
        length=length,
        num_molecules=num_molecules,
        density=density,
        box_type=box_type,
        num_conf=num_conf,
        loop=loop,
    )
    wrapper._builder = builder
    return wrapper
