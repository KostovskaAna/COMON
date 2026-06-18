import json
import os

import numpy as np
import pandas as pd
from moarchiving import get_cmo_archive, get_mo_archive
from pymoo.indicators.igd_plus import IGDPlus


def get_indicator_values(prob_name):
    with open(f'data/problem_data/{prob_name}.json', 'r') as file:
        prob_data = json.load(file)
    return prob_data['nadir'], prob_data['ideal'], prob_data['g_max'], prob_data['pf']


def normalise_F(F, nadir, ideal):
    return [(f - i) / (n - i) for f, n, i in zip(F, nadir, ideal)]


def normalise_G(G, g_max):
    return [g if g_max[i] == 0 else g / g_max[i] for i, g in enumerate(G)]


def correct_log_level(run, log_level):
    if log_level == 'eval':
        return run
    elif log_level == 'gen' or 'final':
        return run[99::100]


def normalise_pf(pf, nadir, ideal):
    return np.array([normalise_F(F, nadir, ideal) for F in pf])


def get_eval_gen(idx, log_level, prob_name):
    n_var = {'COBI1': 2,
             'CRE31': 7,
             'MW1': 30}

    if log_level == 'final':
        return 10000 * n_var[prob_name], 100 * n_var[prob_name]

    elif log_level == 'gen':
        return idx + 1, (idx // 100) + 1

    elif log_level == 'eval':
        return idx + 1, (idx // 100) + 1

    else:
        raise ValueError(f'Log level not handled: {log_level}')


def get_run(df, nadir, ideal, g_max, pf, log_level, prob_name):
    n_obj = len(nadir)
    n_con = len(g_max)

    moa = get_mo_archive(n_obj=n_obj, reference_point=[1] * n_obj)
    igd_plus_ind = IGDPlus(normalise_pf(pf, nadir, ideal))

    run = []
    min_cv = np.inf

    for idx, row in df.iterrows():
        if log_level == 'gen' and idx % 100 == 0:
            moa = get_mo_archive(n_obj=n_obj, reference_point=[1] * n_obj)

        row = list(row)

        F = normalise_F(row[:n_obj], nadir, ideal)
        G = normalise_G(row[-n_con:], g_max)

        cv = sum([max(0, g) for g in G])
        min_cv = min(min_cv, cv)

        if cv == 0:
            moa.add(F)

        icmop = float(max(-1, moa.hypervolume_plus) if min_cv == 0 else -1 - min_cv)
        hv = icmop if icmop > 0 else 0
        igd_plus = np.nan if len(moa) == 0 else igd_plus_ind(np.array(list(moa)))
        cv = -(icmop + 1 if icmop < -1 else 0)

        eval, gen = get_eval_gen(idx, log_level, prob_name)
        run.append([eval, gen, hv, igd_plus, icmop, cv])

    return correct_log_level(run, log_level)


def process_runs(runs):
    data = []
    for i, run in enumerate(runs):
        for values in run:
            data.append(values + [i + 1])
    return pd.DataFrame(data, columns=['eval', 'gen', 'hv', 'igd+', 'icmop', 'cv', 'run'])


def get_runs(df, nadir, ideal, g_max, pf, log_level, prob_name):
    runs = []
    for id in df['run'].unique():
        run_df = df[df['run'] == id]
        run_df = run_df.drop(columns=['run'])
        run_df.reset_index(inplace=True, drop=True)
        runs.append(get_run(run_df, nadir, ideal, g_max, pf, log_level, prob_name))
    return process_runs(runs)


def main():
    folder_path = 'data/raw_data'
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            print(f'Processing {filename}')

            if os.path.exists(f'data/processed_data/{filename}'):
                print('File already processed.')
                continue

            file_path = os.path.join(folder_path, filename)
            df = pd.read_csv(file_path)

            alg_name, prob_name, log_level, platform = filename[:-4].split('_')
            nadir, ideal, g_max, pf = get_indicator_values(prob_name)

            runs_df = get_runs(df, nadir, ideal, g_max, pf, log_level, prob_name)

            runs_df.to_csv(f'data/processed_data/{filename}', index=False)


if __name__ == '__main__':
    main()

    # folder_path = 'data/raw_data'
    # for filename in os.listdir(folder_path):
    #     if 'final_platemo' in filename:
    #         file_path = os.path.join(folder_path, filename)
    #         df = pd.read_csv(file_path)
    #
    #         run_dfs = []
    #         for id in df['run'].unique():
    #             run_df = df[df['run'] == id]
    #             run_df = run_df.tail(100)
    #             run_dfs.append(run_df)
    #
    #         final_df = pd.concat(run_dfs, ignore_index=True)
    #
    #         final_df.to_csv(f'data/raw_data/{filename}', index=False)
