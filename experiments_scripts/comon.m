%% Experiment configuration
BaseURL     = 'http://127.0.0.1:8000';
Problems    = {'MW1'};
Algorithms  = {@MOEADD};

RunsPerSetting = 15;
PopSize        = 100;

% Optional: choose where to write logs
LogDir = fullfile(pwd, 'platemo_logs');
if ~exist(LogDir, 'dir')
    mkdir(LogDir);
end

for a = 1:numel(Algorithms)
    AlgHandle = Algorithms{a};
    AlgName   = func2str(AlgHandle);

    for p = 1:numel(Problems)
        ProbName = Problems{p};

        % Determine evaluation budget from problem dimension
        meta = webread(BaseURL + "/meta", "problem", ProbName);
        D    = meta.n_var;
        FE   = 10000 * D;

        % Log file per (algorithm, problem)
        LogFile = fullfile(LogDir, sprintf('%s_%s_platemo.csv', AlgName, ProbName));

        % Start fresh for this combination
        if exist(LogFile, 'file') == 2
            delete(LogFile);
        end

        fprintf('\nAlgorithm: %s | Problem: %s | D = %d | FE = %d\n', AlgName, ProbName, D, FE);
        fprintf('Logging to: %s\n', LogFile);

        for run = 1:RunsPerSetting
            fprintf('  Run %02d / %02d\n', run, RunsPerSetting);
            rng(run, 'twister');

            platemo( ...
                'algorithm',  AlgHandle, ...
                'problem',    {@FastAPIProblem, BaseURL, ProbName, LogFile, run}, ...
                'N',          PopSize, ...
                'maxFE', FE ...
            );
        end
    end
end
