import os
from pathlib import Path

import pytest
from jobflow import run_locally

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker


class DummyBuilder:
    def __init__(self, OutDir):
        self.OutDir = OutDir
        self.Build_called = False

    def Build(self):
        self.Build_called = True


@pytest.fixture
def dummy_builder(monkeypatch, tmp_path):
    # Monkeypatch build_amorphous_structure to return DummyBuilder
    def fake_build(*args, **kwargs):
        outdir = str(tmp_path / "amor")
        os.makedirs(outdir, exist_ok=True)
        b = DummyBuilder(outdir)
        b.Build()
        return b

    monkeypatch.setattr(
        "atomate2.dmax.jobs.structure_generation.build_amorphous_structure", fake_build
    )
    return tmp_path


def test_psp_structure_maker(dummy_builder, tmp_path):
    # Set up maker
    maker = PSPStructureMaker(
        smiles="C[*]",
        left_cap="A[*]",
        right_cap="[*]B",
        length=2,
        num_molecules=3,
        density=0.8,
        box_type="c",
        out_dir=Path(tmp_path / "amor"),
        num_conf=1,
        loop=False,
    )
    maker.name = "build_test"
    # Create job
    job = maker.make()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    # Run locally
    responses = run_locally(job, create_folders=True, ensure_success=True)
    os.chdir(cwd)
    resp = responses[job.uuid][1]
    output = resp.output
    # Should be DummyBuilder instance
    assert isinstance(output, DummyBuilder)
    # Build was called on the builder
    assert output.Build_called is True
    # OutDir attribute matches
    assert os.path.isdir(output.OutDir)
