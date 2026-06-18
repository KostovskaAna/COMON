import json
import os.path

import numpy as np
import pandas as pd

from cmo.problems.factory import get_problem

from jmetal.algorithm.multiobjective import SPEA2
from jmetal.operator.crossover import SBXCrossover
from jmetal.operator.mutation import PolynomialMutation
from jmetal.util.termination_criterion import StoppingByEvaluations
from jmetal.core.problem import FloatProblem
from jmetal.core.solution import FloatSolution
from jmetal.util.observer import Observer
from jmetal.util.comparator import DominanceWithConstraintsComparator

from cobi_problem import get_cobi_problem


class PymooFloatProblemAdapter(FloatProblem):
    """
    Adapter from pymoo-style FloatProblem to jMetalPy FloatProblem.

    Important convention difference:

    pymoo:
        feasible if G <= 0

    jMetalPy:
        feasible if constraints >= 0

    Therefore:
        jMetalPy constraint = -pymoo G
    """

    def __init__(self, pymoo_problem, check_constraints: bool = False):
        super().__init__()

        self.pymoo_problem = pymoo_problem
        self.check_constraints = check_constraints

        xl = np.array(pymoo_problem.xl, dtype=float).ravel()
        xu = np.array(pymoo_problem.xu, dtype=float).ravel()

        self.lower_bound = xl.tolist()
        self.upper_bound = xu.tolist()

        self._n_var = len(self.lower_bound)
        self._n_obj = int(pymoo_problem.n_obj)
        self._n_constr = int(getattr(pymoo_problem, "n_constr", 0))

        self.obj_directions = [self.MINIMIZE] * self._n_obj
        self.obj_labels = [f"f{i + 1}" for i in range(self._n_obj)]

    def number_of_variables(self) -> int:
        return self._n_var

    def number_of_objectives(self) -> int:
        return self._n_obj

    def number_of_constraints(self) -> int:
        return self._n_constr

    def name(self) -> str:
        if hasattr(self.pymoo_problem, "name"):
            try:
                return self.pymoo_problem.name()
            except TypeError:
                pass

        return "PymooWrappedProblem"

    def evaluate(self, solution: FloatSolution) -> FloatSolution:
        x = np.array(solution.variables, dtype=float).reshape(1, -1)

        if self._n_constr > 0:
            F, G = self.pymoo_problem.evaluate(
                x,
                return_values_of=["F", "G"],
            )
        else:
            F = self.pymoo_problem.evaluate(
                x,
                return_values_of=["F"],
            )

        F = np.asarray(F, dtype=float).reshape(-1)

        for i in range(self._n_obj):
            solution.objectives[i] = float(F[i])

        if self._n_constr > 0:
            G = np.asarray(G, dtype=float).reshape(-1)

            # Keep pymoo-style constraints for CSV/logging:
            # feasible if G <= 0
            solution.pymoo_constraints = [float(g) for g in G]

            # Convert to jMetalPy-style constraints:
            # feasible if constraint >= 0
            for i in range(self._n_constr):
                solution.constraints[i] = -float(G[i])

            if self.check_constraints:
                pymoo_feasible = bool(np.all(G <= 0.0))
                jmetal_feasible = bool(
                    np.all(np.asarray(solution.constraints, dtype=float) >= 0.0)
                )

                if pymoo_feasible != jmetal_feasible:
                    raise RuntimeError(
                        "Constraint sign conversion failed. "
                        f"pymoo G={G}, "
                        f"jMetalPy constraints={solution.constraints}"
                    )

        return solution


class EvaluationLogger(Observer):
    """
    Logs every solution exposed through the jMetalPy observable.

    CSV constraints are intentionally stored in pymoo convention:
        feasible if g <= 0

    The internal jMetalPy constraints are still:
        feasible if constraint >= 0
    """

    def __init__(self):
        super().__init__()
        self.data = []

    def update(self, *args, **kwargs):
        solutions = kwargs.get("SOLUTIONS")
        evaluations = kwargs.get("EVALUATIONS")

        if solutions is None:
            return

        if evaluations is None:
            evaluations = -1

        for sol in solutions:
            constraints_for_csv = getattr(sol, "pymoo_constraints", sol.constraints)

            row = (
                list(sol.objectives)
                + list(constraints_for_csv)
                + [int(evaluations)]
            )

            self.data.append(row)


def get_cmop(prob_name):
    problems = {
        "COBI1": get_cobi_problem(),
        "CRE31": get_problem("cre31"),
        "MW1": get_problem("mw1", n_var=30),
    }

    return problems[prob_name]


def get_columns(problem):
    return (
        [f"f{i + 1}" for i in range(problem.n_obj)]
        + [f"g{i + 1}" for i in range(problem.n_constr)]
        + ["evaluations", "run"]
    )


def get_nadir(prob_name):
    with open(f"data/problem_data/{prob_name}.json", "r") as file:
        prob_data = json.load(file)

    return prob_data["nadir"]


def get_data(
    log_level,
    prob_name,
    n_runs,
    evals_mul,
    overwrite: bool = False,
    check_constraints: bool = False,
):
    path = f"data/raw_data/SPEA2_{prob_name}_{log_level}_jmetalpy.csv"

    if os.path.exists(path) and not overwrite:
        print(f"Skipping existing file: {path}")
        return

    pymoo_problem = get_cmop(prob_name)
    n_evals = evals_mul * pymoo_problem.n_var

    data = []

    for run_id in range(1, n_runs + 1):
        print(f"Running {prob_name}, run {run_id}")

        problem = PymooFloatProblemAdapter(
            pymoo_problem,
            check_constraints=check_constraints,
        )

        algorithm = SPEA2(
            problem=problem,
            population_size=100,
            offspring_population_size=100,
            mutation=PolynomialMutation(
                probability=1.0 / problem.number_of_variables()
            ),
            crossover=SBXCrossover(
                probability=1.0
            ),
            termination_criterion=StoppingByEvaluations(
                max_evaluations=n_evals
            ),

            # Critical fix:
            # Make SPEA2 use constraints during dominance comparisons.
            dominance_comparator=DominanceWithConstraintsComparator(),
        )

        logger = EvaluationLogger()
        algorithm.observable.register(logger)

        algorithm.run()

        for row in logger.data:
            data.append(row + [run_id])

    df = pd.DataFrame(data, columns=get_columns(pymoo_problem))
    df.to_csv(path, index=False)

    print(f"Saved: {path}")


def main():
    n_runs = 15
    evals_mul = 10000

    problem_names = ["COBI1", "CRE31", "MW1"]
    log_level = "gen"

    for prob_name in problem_names:
        get_data(
            log_level=log_level,
            prob_name=prob_name,
            n_runs=n_runs,
            evals_mul=evals_mul,

            # Set True if you want to regenerate existing CSVs.
            overwrite=False,

            # Set True for debugging. Set False for speed.
            check_constraints=False,
        )


if __name__ == "__main__":
    main()
