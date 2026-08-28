import pytest
from jobflow import Flow

from atomate2.dmax.flows.core import NumCyclesConvergenceFlow, StrainSizeConvergenceFlow


@pytest.mark.parametrize(
    "flow_class,flow_name",
    [
        (StrainSizeConvergenceFlow, "strain_size_convergence_flow"),
        (NumCyclesConvergenceFlow, "num_cycles_convergence_flow"),
    ],
)
def test_convergence_flows_make_return_flow(flow_class, flow_name, tmp_path):
    # instantiate flow
    flow = flow_class()
    assert hasattr(flow, "make"), "Flow class must implement make method"
    # simulate restart file path
    # ensure directory exists
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    restart_file = str(work_dir / "restart.equil")
    # make and assert Flow
    result_flow = flow.make(restart_file)
    assert isinstance(result_flow, Flow)
    assert result_flow.name == flow_name
    # must have at least one job
    assert hasattr(result_flow, "jobs") and len(result_flow.jobs) >= 1
    # output should be accessible
    assert hasattr(result_flow, "output")
