import os.path

import cma
import numpy as np
from cmo.problems.factory import get_problem
import pandas as pd
from pymoo.core.individual import calc_cv
from scipy.optimize import minimize

from cobi_problem import get_cobi_problem


def get_weights(n, dimensions=2):
    """
    Generates weights for 2 or 3 dimensions that sum to 1.

    Parameters:
    - n: int, the number of weight combinations to generate
    - dimensions: int, the number of dimensions (must be 2 or 3)

    Returns:
    - List of tuples, where each tuple contains weights for the dimensions that sum to 1.
    """
    if dimensions == 2:
        weights_1 = np.linspace(0, 1, n)
        weights_2 = 1 - weights_1
        return list(zip(weights_1, weights_2))
    elif dimensions == 3:
        return np.random.dirichlet(np.ones(dimensions), size=n).tolist()
    else:
        raise ValueError("This function only supports 2 or 3 dimensions.")


def get_cmop(prob_name):
    problems = {
        'COBI1': get_cobi_problem(),
        'CRE31': get_problem('cre31'),
        'MW1': get_problem('mw1', n_var=30)
    }
    return problems[prob_name]


def get_columns(problem):
    return [f'f{i + 1}' for i in range(problem.n_obj)] + [f'g{i + 1}' for i in range(problem.n_constr)] + ['run']


def cobyla_run(problem, run_id, evals_mul=10000):
    n_evals = evals_mul * problem.n_var
    n_weights = 100 * problem.n_obj
    n_gens = n_evals // n_weights

    def objective(x, weights, problem):
        F, _ = problem.evaluate(x)
        f = np.dot(F, weights)
        return f

    def constraint(x, problem):
        _, G = problem.evaluate(x)
        cv = calc_cv(G)
        bounds = np.concatenate([x - problem.xl, problem.xu - x])
        return np.concatenate([bounds, [-cv]])

    def callback(x):
        solutions.append(x)

    x0 = np.random.uniform(low=problem.xl, high=problem.xu)

    cons = {'type': 'ineq', 'fun': lambda x: constraint(x, problem)}

    all_solutions = [[] for _ in range(n_gens)]
    for weights in get_weights(n_weights, problem.n_obj):

        solutions = []
        minimize(objective,
                 x0,
                 args=(weights, problem),
                 constraints=cons,
                 callback=callback,
                 method='COBYLA',
                 options={'disp': False, 'maxiter': n_gens})

        for i in range(n_gens):
            if i >= len(solutions):
                all_solutions[i].append(solutions[-1])
            else:
                all_solutions[i].append(solutions[i])

    data = []
    for X in all_solutions:
        F, G = problem.evaluate(np.clip(X, problem.xl, problem.xu))
        for f, g in zip(F, G):
            data.append(list(f) + list(g) + [run_id])

    return data


def cmaes_run(problem, run_id, evals_mul=10000):
    n_evals = evals_mul * problem.n_var
    popsize = 10
    num_weights = 100 * problem.n_obj // popsize
    P = 100
    n_gens = n_evals // P

    options = {
        'bounds': [problem.xl, problem.xu],
        'popsize': popsize,
        'verbose': -9,
        'verb_log': 0,
        'verb_disp': 0
    }
    starting_sols = [np.random.uniform(low=problem.xl, high=problem.xu) for _ in range(num_weights)]
    algorithms = [cma.CMAEvolutionStrategy(starting_sols[i], 0.5, options) for i in range(num_weights)]

    gen = 0
    while gen < n_gens:
        gen += 1

        for i in range(len(algorithms)):
            if algorithms[i].stop():
                best_solution = algorithms[i].result.xbest
                algorithms[i] = cma.CMAEvolutionStrategy(best_solution, 0.5, options)

        all_F, all_G = [], []
        for es, weights in zip(algorithms, get_weights(num_weights, problem.n_obj)):
            solutions = es.ask()
            obj_vals = []
            for x in solutions:
                F, G = problem.evaluate(x)
                f = np.dot(F, weights)
                cv = calc_cv(G)
                obj_vals.append(f + cv)
                all_F.append(F), all_G.append(G)
            es.tell(solutions, obj_vals)

        if gen == n_gens:
            data = []
            for f, g in zip(all_F, all_G):
                data.append(list(f) + list(g) + [run_id])
            return data


def get_data(alg_name, recording_level, prob_name, n_runs, evals_mul):
    path = f'data/raw_data/{alg_name}_{prob_name}_{recording_level}_author.csv'
    if os.path.exists(path):
        return

    problem = get_cmop(prob_name)

    algorithm_funcs = {'CMA-ES': cmaes_run,
                       'COBYLA': cobyla_run}

    alg_fun = algorithm_funcs[alg_name]

    data = []
    for run_id in range(1, n_runs + 1):
        data += alg_fun(problem, run_id, evals_mul=evals_mul)

    pd.DataFrame(data, columns=get_columns(problem)).to_csv(path, index=False)


def main():
    n_runs = 15
    evals_mul = 10000

    algorithm_names = ['CMA-ES', 'COBYLA']
    problem_names = ['COBI1', 'CRE31', 'MW1']
    log_levels = ['final', 'gen']

    for alg_name, log_level in zip(algorithm_names, log_levels):
        for prob_name in problem_names:
            print(f'Running {alg_name} on {prob_name}')
            get_data(alg_name, log_level, prob_name, n_runs, evals_mul)


if __name__ == '__main__':
    main()
