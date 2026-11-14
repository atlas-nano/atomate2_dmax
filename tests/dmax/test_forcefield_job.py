import os

import pytest
from jobflow import run_locally

from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker


class DummyBuilder:
    def __init__(self, OutDir):
        self.OutDir = OutDir

    def get_opls(self, output_fname):
        # simulate generating a file
        with open(output_fname, "w") as f:
            f.write("dummy opls data")


@pytest.fixture
def tmp_amor(tmp_path):
    outdir = str(tmp_path / "amor")
    os.makedirs(outdir)
    return DummyBuilder(outdir)


def test_forcefield_maker_auto(tmp_amor, tmp_path, monkeypatch):
    # monkeypatch parametrize_auto to use our dummy builder
    # ForceFieldMaker.make will call parametrize_auto internally
    # So we let the default parametrize_auto use ligpargen first

    # Create maker
    maker = ForceFieldMaker()
    maker.name = "ff_test"

    # Run job
    job = maker.make(tmp_amor)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    responses = run_locally(job, create_folders=True, ensure_success=True)
    os.chdir(cwd)

    # Extract output path
    resp = responses[job.uuid][1]
    output = resp.output
    # Check file was created and returned
    assert isinstance(output, str)
    assert os.path.isfile(output)
    assert output.endswith("amor_opls.lmps")
