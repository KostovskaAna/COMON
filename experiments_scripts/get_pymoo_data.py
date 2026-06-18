import os.path

from cmo.problems.factory import get_problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.sms import SMSEMOA
from pymoo.operators.crossover.sbx import SBX
# from pymoode.algorithms import GDE3
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


def get_data(alg_name, recording_level, prob_name, n_runs, evals_mul):
    path = f'data/raw_data/{alg_name}_{prob_name}_{recording_level}_pymoo.csv'
    if os.path.exists(path):
        return

    problem = get_cmop(prob_name)

    algorithms = {'NSGA-II': NSGA2,
                  'SMS-EMOA': SMSEMOA,
                  # 'GDE3': GDE3
                  }

    data = []
    for run_id in range(1, n_runs + 1):
        algorithm = algorithms[alg_name](
            crossover=SBX(eta=20, prob=0.9)
        )
        algorithm.setup(problem, termination=('n_evals', evals_mul * problem.n_var), seed=run_id, verbose=False)

        while algorithm.has_next():
            algorithm.next()

            if recording_level == 'eval' or recording_level == 'gen':
                for f, g in zip(algorithm.result().pop.get('F'), algorithm.result().pop.get('G')):
                    data.append(list(f) + list(g) + [run_id])

        if recording_level == 'final':
            for f, g in zip(algorithm.result().pop.get('F'), algorithm.result().pop.get('G')):
                data.append(list(f) + list(g) + [run_id])

    pd.DataFrame(data, columns=get_columns(problem)).to_csv(path, index=False)


def main():
    n_runs = 15
    evals_mul = 10000

    problem_names = ['COBI1', 'CRE31', 'MW1']
    algorithm_names = ['NSGA-II']#, 'SMS-EMOA', 'GDE3']
    log_levels = ['eval']#, 'final', 'eval']

    for alg_name, log_level in zip(algorithm_names, log_levels):
        for prob_name in problem_names:
            print(f'Running {alg_name} on {prob_name}')
            get_data(alg_name, log_level, prob_name, n_runs, evals_mul)


if __name__ == '__main__':
    main()
