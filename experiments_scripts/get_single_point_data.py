import os.path

import numpy as np
from cmo.problems.factory import get_problem
import pandas as pd

from cobi_problem import get_cobi_problem


def get_cmop(prob_name):
    problems = {
        'COBI1': get_cobi_problem(),
        'CRE31': get_problem('cre31'),
        'MW1': get_problem('mw1', n_var=30)
    }
    return problems[prob_name]


def get_columns(problem):
    return [f'f{i + 1}' for i in range(problem.n_obj)] + [f'g{i + 1}' for i in range(problem.n_constr)] + ['run']


def random_search_csops_run(problem, run_id, num_csops=10, evals_mul=10000):
    n_var = problem.n_var
    xl, xu = problem.xl, problem.xu
    n_obj = problem.n_obj
    n_evals = evals_mul * problem.n_var

    weights = np.random.rand(num_csops, n_obj)
    weights /= np.sum(weights, axis=1, keepdims=True)

    data = []
    for _ in weights:
        for _ in range(n_evals // len(weights)):
            x = xl + np.random.rand(n_var) * (xu - xl)
            F, G = problem.evaluate(x)
            row = list(F) + list(G) + [run_id]
            data.append(row)

    return data


def iterative_local_search_run(problem, run_id, evals_mul=10000, step_size=0.1):
    """
    Iterative local search:
    - Single starting point
    - Local perturbations around current best
    - Constraint-aware acceptance
    - Logs [F..., G..., run_id] for every evaluation
    """

    n_var = problem.n_var
    xl, xu = np.array(problem.xl), np.array(problem.xu)
    n_evals = evals_mul * n_var

    data = []

    # --- Helper functions -------------------------------------------------

    def is_feasible(G):
        G = np.array(G)
        if G.size == 0:
            return True
        return np.all(G <= 0.0)

    def total_violation(G):
        G = np.array(G)
        if G.size == 0:
            return 0.0
        return np.sum(np.maximum(G, 0.0))

    def better(F_new, G_new, F_cur, G_cur):
        """
        Return True if (F_new, G_new) is better than (F_cur, G_cur).
        Assumes minimization on the first objective F[0].
        """
        feasible_new = is_feasible(G_new)
        feasible_cur = is_feasible(G_cur)

        if feasible_new and not feasible_cur:
            return True
        if not feasible_new and feasible_cur:
            return False

        if feasible_new and feasible_cur:
            # Both feasible: compare first objective
            return F_new[0] < F_cur[0]

        # Both infeasible: smaller total violation is better
        return total_violation(G_new) < total_violation(G_cur)

    def log_eval(F, G):
        row = list(F) + list(G) + [run_id]
        data.append(row)

    # --- Initialization ---------------------------------------------------

    # Random initial solution
    x_cur = xl + np.random.rand(n_var) * (xu - xl)
    F_cur, G_cur = problem.evaluate(x_cur)
    log_eval(F_cur, G_cur)

    # --- Main loop --------------------------------------------------------

    for _ in range(1, n_evals):
        # Local perturbation: uniform in [-step_size, +step_size] around current
        perturbation = (np.random.rand(n_var) * 2.0 - 1.0) * step_size * (xu - xl)
        x_new = x_cur + perturbation

        # Keep within bounds
        x_new = np.minimum(np.maximum(x_new, xl), xu)

        F_new, G_new = problem.evaluate(x_new)
        log_eval(F_new, G_new)

        # Accept if better according to our comparison rule
        if better(F_new, G_new, F_cur, G_cur):
            x_cur, F_cur, G_cur = x_new, F_new, G_new

    return data


def random_search_run(problem, run_id, evals_mul=10000):
    n_var = problem.n_var
    xl, xu = problem.xl, problem.xu
    n_evals = evals_mul * problem.n_var

    data = []
    for _ in range(n_evals):
        x = xl + np.random.rand(n_var) * (xu - xl)
        F, G = problem.evaluate(x)
        row = list(F) + list(G) + [run_id]
        data.append(row)

    return data


def get_data(alg_name, recording_level, prob_name, n_runs, evals_mul):
    path = f'data/raw_data/{alg_name}_{prob_name}_{recording_level}_author.csv'
    if os.path.exists(path):
        return

    problem = get_cmop(prob_name)

    algorithm_funcs = {'CSOP-RS': random_search_csops_run,
                       'ILS': iterative_local_search_run,
                       'RS': random_search_run}

    alg_fun = algorithm_funcs[alg_name]

    data = []
    for run_id in range(1, n_runs + 1):
        data += alg_fun(problem, run_id, evals_mul=evals_mul)

    pd.DataFrame(data, columns=get_columns(problem)).to_csv(path, index=False)


def main():
    n_runs = 15
    evals_mul = 10000

    algorithm_names = ['CSOP-RS', 'ILS', 'RS']
    problem_names = ['COBI1', 'CRE31', 'MW1']
    log_levels = ['eval', 'gen', 'gen']

    for alg_name, log_level in zip(algorithm_names, log_levels):
        for prob_name in problem_names:
            print(f'Running {alg_name} on {prob_name}')
            get_data(alg_name, log_level, prob_name, n_runs, evals_mul)


if __name__ == '__main__':
    main()
