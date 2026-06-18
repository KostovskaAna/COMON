import json
import os.path

from cmo.problems.factory import get_problem
import pandas as pd

from cobi_problem import get_cobi_problem
from comocma.como import best_chv_restart_kernel, Sofomore, get_cmas


def get_cmop(prob_name):
    problems = {
        'COBI1': get_cobi_problem(),
        'CRE31': get_problem('cre31'),
        'MW1': get_problem('mw1', n_var=30)
    }
    return problems[prob_name]


def get_columns(problem):
    return [f'f{i + 1}' for i in range(problem.n_obj)] + [f'g{i + 1}' for i in range(problem.n_constr)] + ['run']


def get_nadir(prob_name):
    with open(f'data/problem_data/{prob_name}.json', 'r') as file:
        prob_data = json.load(file)
    return prob_data['nadir']


def get_data(log_level, prob_name, n_runs, evals_mul):
    path = f'data/raw_data/COMO-CMA_{prob_name}_{log_level}_cma.csv'
    if os.path.exists(path):
        return

    problem = get_cmop(prob_name)
    n_evals = evals_mul * problem.n_var

    data = []
    for run_id in range(1, n_runs + 1):
        print(f'Run {run_id}')
        moes = Sofomore(get_cmas([problem.n_var * [0]], 0.2, inopts={'bounds': [problem.xl, problem.xu]}),
                        opts={'restart': best_chv_restart_kernel},
                        reference_point=get_nadir(prob_name))

        eval = 0
        while not moes.stop() and eval < n_evals:
            X = moes.ask("all")
            F, G = map(list, zip(*[problem.evaluate(x) for x in X]))
            moes.tell(X, F, G)
            eval += len(F)

            for f, g in zip(F, G):
                data.append(list(f) + list(g) + [run_id])

    pd.DataFrame(data, columns=get_columns(problem)).to_csv(path, index=False)


def main():
    n_runs = 15
    evals_mul = 10000

    problem_names = ['COBI1']#, 'MW1']
    log_level = 'eval'

    for prob_name in problem_names:
        print(f'Running {prob_name}')
        get_data(log_level, prob_name, n_runs, evals_mul)


if __name__ == '__main__':
    main()
