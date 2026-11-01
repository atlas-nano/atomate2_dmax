import os

import pytest

from atomate2.dmax.generators.forcefield import parametrize_auto, parametrize_ligpargen


class DummyBuilder:
    def __init__(self, OutDir):
        self.OutDir = OutDir
        self.called = False
        self.last_output = None

    def get_opls(self, output_fname):
        self.called = True
        self.last_output = output_fname
        # simulate output file creation
        with open(output_fname, "w") as f:
            f.write("LAMMPS data dummy")


@pytest.fixture
def tmp_builder(tmp_path):
    outdir = str(tmp_path / "amor")
    os.makedirs(outdir)
    return DummyBuilder(outdir)


def test_parametrize_ligpargen(tmp_builder):
    # No output file provided, should default to 'amor_opls.lmps'
    path = parametrize_ligpargen(tmp_builder)
    expected = os.path.join(tmp_builder.OutDir, "amor_opls.lmps")
    assert path == expected
    assert tmp_builder.called is True
    # file should exist
    assert os.path.isfile(expected)


def test_parametrize_auto_only_ligpargen(tmp_builder, monkeypatch):
    # monkeypatch ligpargen to custom return
    def fake_lig(amor):
        return "ligpargen_path.lmps"

    monkeypatch.setattr(
        "atomate2.dmax.generators.forcefield.parametrize_ligpargen", fake_lig
    )
    result = parametrize_auto(tmp_builder)
    assert result == "ligpargen_path.lmps"


def test_parametrize_auto_fallback(monkeypatch, tmp_builder):
    # ligpargen fails, foyer succeeds
    calls = []

    def fake_lig(amor):
        calls.append("lig")
        raise RuntimeError("no lig")

    def fake_foyer(amor):
        calls.append("foyer")
        return "foyer_path.lmps"

    monkeypatch.setattr(
        "atomate2.dmax.generators.forcefield.parametrize_ligpargen", fake_lig
    )
    monkeypatch.setattr(
        "atomate2.dmax.generators.forcefield.parametrize_foyer", fake_foyer
    )
    result = parametrize_auto(tmp_builder)
    assert result == "foyer_path.lmps"
    assert calls == ["lig", "foyer"]
