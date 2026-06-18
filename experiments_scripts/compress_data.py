import os

import pandas as pd


def check_change(row, previous_row):
    _, _, hv, igd_plus, icmop, cv, run = row
    _, _, prev_hv, prev_igd_plus, prev_icmop, prev_cv, prev_run = previous_row

    if hv > prev_hv or igd_plus < prev_igd_plus or icmop > prev_icmop or cv < prev_cv or run != prev_run:
        return True

    return False


def compress_data(df):
    compressed_data = []
    previous_row = None
    for idx, row in df.iterrows():
        if len(compressed_data) == 0 or check_change(row, previous_row):
            compressed_data.append(row)

        previous_row = row

    return pd.DataFrame(compressed_data, columns=df.columns)


def main():
    folder_path = 'data/processed_data'
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            print(f'Compressing {filename}')

            if os.path.exists(f'data/compressed_data/{filename}'):
                print('File already compressed.')
                continue

            file_path = os.path.join(folder_path, filename)
            df = pd.read_csv(file_path)

            compressed_df = compress_data(df)

            compressed_df.to_csv(f'data/compressed_data/{filename}', index=False)


if __name__ == '__main__':
    main()
