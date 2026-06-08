# The pymfm framework
#
# Solver factory — picks the first available solver from the configured
# preference list.  Add new solvers to config.settings.solver_preference.

import logging
from typing import Optional

from pyomo.environ import SolverFactory

from pymfm.config import settings

log = logging.getLogger(__name__)


def get_solver():
    """Return the first available Pyomo solver from the preference list.

    Tries each name in ``settings.solver_preference`` in order and returns the
    first one that is actually installed.  Raises ``RuntimeError`` if none is
    found.
    """
    for name in settings.solver_preference:
        solver = SolverFactory(name)
        if solver.available():
            log.info("Using solver: %s", name)
            return solver
        log.debug("Solver '%s' is not available, trying next.", name)

    raise RuntimeError(
        f"No solver is available.  Tried: {settings.solver_preference}.  "
        "Install at least one of: gurobi, scip, highs, or glpk."
    )
