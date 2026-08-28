# Import the module under test
from atomate2.dmax.generators.polymer_structure import build_amorphous_structure


def test_build_amorphous_structure(monkeypatch, tmp_path):
    # Dummy builder that records arguments
    class DummyBuilder:
        def __init__(self, df, density, box_type, OutDir):
            # store inputs
            self.df = df
            self.density = density
            self.box_type = box_type
            self.OutDir = OutDir
            self.Build_called = False

        def Build(self):
            self.Build_called = True

    # Monkeypatch PSPBuilder to our dummy
    import atomate2.dmax.generators.polymer_structure as mod

    monkeypatch.setattr(mod, "PSPBuilder", DummyBuilder)

    smiles = "C[*]"
    left = "A[*]"
    right = "[*]B"
    length = 3
    num_molecules = 4
    density = 0.5
    box_type = "c"
    out_dir = str(tmp_path / "build_out")

    builder = build_amorphous_structure(
        smiles=smiles,
        left_cap=left,
        right_cap=right,
        length=length,
        num_molecules=num_molecules,
        density=density,
        box_type=box_type,
        out_dir=out_dir,
        num_conf=2,
        loop=True,
    )
    # Verify returned object
    assert isinstance(builder, DummyBuilder)
    # Verify that Build was called
    assert builder.Build_called is True
    # Check that DataFrame passed to builder contains correct values
    df = builder.df
    assert df.loc[0, "smiles"] == smiles
    assert df.loc[0, "LeftCap"] == left
    assert df.loc[0, "RightCap"] == right
    assert df.loc[0, "Len"] == length
    assert df.loc[0, "Num"] == num_molecules
    assert builder.OutDir == out_dir
