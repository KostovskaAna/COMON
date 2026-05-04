from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import RDF, XSD
from tqdm import tqdm

import re
from os import path


def read_configurations(file_path: str, algorithm: str):
    '''
    Reads the results/paramterers folder for the parameter values
    '''
    with open(file_path) as in_file:
        text = in_file.read()

    best_configurations = text.split("# Best configurations as commandlines (first number is the configuration ID; same order as above):")[-1]
    best_configurations = [line for line in best_configurations.split('\n') if line.strip()] # Remove empty lines
    
    instances = re.findall(r'instances = .*', text, flags=re.MULTILINE)[0]
    instance_params = instances.split('"')[1] # Get params between "
    instance_params_pairs = instance_params.split("--")
    problem = instance_params_pairs[0].strip()

    instance_params = {
        "problemName": problem
    }
    for instance_param in instance_params_pairs[1:]:
        parameter_name, parameter_value = instance_param.strip().split()
        instance_params[parameter_name] = parameter_value

    parameters = {}
    for configuration in best_configurations:
        parameter_pairs = configuration.split("--")
        id_ = parameter_pairs[0].strip()
        parameters[id_]  = {
            "algorithm": algorithm,
            **instance_params
        }

        for parameter in parameter_pairs[1:]:
            parameter_name, parameter_value = parameter.strip().split()
            parameters[id_][parameter_name] = parameter_value
            
    return parameters

def read_quality_indicator(file_path: str):
    '''
    Reads the results/indicators folder for the quality indicators
    '''
    indicators = {}
    with open(file_path) as f:
        for line in f:
            name, value = "HV", line.strip()
            indicators[name] = value
    return indicators

def get_type(value: str):
    '''
        Receives a string as a parameter and returns it with the correct
        type as well as its type as a string.

        Example: '31' -> (31, 'integer')
    '''
    type_ = 'string'
    result = value
    try:
        result = int(value)
        type_ = 'integer'
    except ValueError:
        try:
            result = float(value)
            type_ = 'double'
        except ValueError:
            result = value
            type_ = 'string'

    return result, type_

def get_algorithm(configuration: dict):
    '''
        Receives a configuration.
        Returns the URI of the algorithm used for that configuration.
    '''
    algorithm = configuration['algorithm'].replace('Auto', '').replace('Simple', '')
    del configuration['algorithm']
    return algorithm

def get_problem(configuration: dict):
    '''
        Receives a configuration.
        Returns the URI of the problem used for that configuration.
    '''
    # ZDT 5 is a unused binary problem
    problems = [
        # WFG
        'WFG1', 'WFG2', 'WFG3', 'WFG4', 'WFG5', 'WFG6', 'WFG7', 'WFG8', 'WFG9',
        # DTLZ 2D
        'DTLZ1_2D', 'DTLZ2_2D', 'DTLZ3_2D', 'DTLZ4_2D', 'DTLZ5_2D', 'DTLZ6_2D', 'DTLZ7_2D',
        # DTLZ
        'DTLZ1', 'DTLZ2', 'DTLZ3', 'DTLZ4', 'DTLZ5', 'DTLZ6', 'DTLZ7',
        # ZDT
        'ZDT1', 'ZDT2', 'ZDT3', 'ZDT4', 'ZDT6',
        # RE
        'RE21', 'RE22', 'RE23', 'RE24', 'RE25', 'RE31', 'RE32', 'RE33', 'RE34', 'RE35', 'RE36', 'RE37', 'RE41', 'RE42', 'RE61', 'RE91',
        # LZ09
        'LZ09F1', 'LZ09F2', 'LZ09F3', 'LZ09F4', 'LZ09F5', 'LZ09F6', 'LZ09F7', 'LZ09F8', 'LZ09F9',
        # UF
        'UF10', 'UF1', 'UF2', 'UF3', 'UF4', 'UF5', 'UF6', 'UF7', 'UF8', 'UF9',
        # GLT
        'GLT1', 'GLT2', 'GLT3', 'GLT4', 'GLT5', 'GLT6',
    ]
    problem_name = configuration['problemName'].upper()
    # TODO add all problems
    for problem in problems:
        # TODO Fix if substring matches
        if problem in problem_name:
            return problem
    
    raise ValueError(f"Problem not found: {problem_name}")

def parse_irace(configuration_folder: str, output_file: str, base_graph_file: str = '../moody.owl'):
    '''
    Get all configurations from a irace output folder and generate the RDF graph with the configurations annotated.
    '''
    # Set up namespaces used
    opt = Namespace('http://w3id.org/moody#')

    # Generate new graph
    rdf = Graph()

    # Add ontology to file
    if base_graph_file:
        rdf.parse(base_graph_file, format='nt11')

    # Bind namespaces to prefix
    rdf.bind('opt', opt)
    
    # For each configuration
    configurations = read_configurations(configuration_folder + "/irace.stdout.txt", algorithm=algorithm)
    for configuration_id, configuration in tqdm(configurations.items()):

        experiment_id = configuration_id
        problem = get_problem(configuration)
        algorithm = get_algorithm(configuration)
        # Add experiment
        uri_experiment = URIRef(opt + 'Experiment_' + algorithm + '_' + problem + '_' + experiment_id)
        rdf.add( (uri_experiment, RDF.type, opt.Experiment) )
        rdf.add( (uri_experiment, opt.problemSolved, opt['Problem_' + problem]) )
        rdf.add( (uri_experiment, opt.algorithmUsed, opt['Algorithm_' + algorithm]) )


        number_evaluations = configuration["maximumNumberOfEvaluations"]
        execution_file = path.join(configuration_folder, f"c{configuration_id}-1.stdout")

        indicators = read_quality_indicator(execution_file)

        # Add resolution
        Resolution_id = "0" # Irace only makes one execution
        uri_problem_resolution = URIRef(opt + 'Resolution_' + experiment_id + '_' + problem + '_' + Resolution_id + '_' + number_evaluations)
        rdf.add( (uri_problem_resolution, RDF.type, opt.ProblemResolution) )
        rdf.add( (uri_problem_resolution, opt.partOfExperiment, uri_experiment) )
        value, type_ = get_type(number_evaluations)
        rdf.add( (uri_problem_resolution, opt.currentNumberOfEvaluations, Literal(value, datatype=XSD[type_])) )

        # Add Indicators
        for key, value in indicators.items():
            # Change keys to match the class they represent
            property_name = 'Unknown'
            if key == 'HV' or key == 'NHV':
                key = 'HyperVolume'
                property_name = 'hyperVolumeValue'
            elif key == 'EP':
                key = 'Epsilon'
                property_name = 'epsilonValue'
            elif key == 'IGD':
                key = 'InvertedGenerationalDistance'
                property_name = 'invertedGenerationalDistanceValue'
            elif key == 'IGD+':
                key = 'InvertedGenerationalDistancePlus'
                property_name = 'invertedGenerationalDistancePlusValue'
            elif key == 'SPREAD' or key == 'SP':
                key = 'Spread'
                property_name = 'spreadValue'
            else:
                raise ValueError('Unknown Quality Indicator ' + key)

            uri_indicator = URIRef(opt + 'QualityIndicator_' + key)
            uri_indicator_value = URIRef(opt + 'QualityIndicatorValue_' + key + '_' + value)
            rdf.add( (uri_indicator_value, RDF.type, opt['QualityIndicatorValue']) )
            rdf.add( (uri_indicator_value, opt.valueOfIndicator, uri_indicator) )
            rdf.add( (uri_problem_resolution, opt.indicatorValue, uri_indicator_value) )
            rdf.add( (uri_experiment, opt.evaluatedBy, uri_indicator) )

            value, type_ = get_type(value)
            rdf.add( (uri_indicator_value, opt[property_name], Literal(value, datatype=XSD[type_])) )

            # Add Parameters
            for key, value in configuration.items():
                # Change keys to match the class they represent
                # Capitalize the first letter
                if key ==  'sbxDistributionIndex':
                    key = 'sbxCrossoverDistributionIndex'
                elif key == "mutationProbabilityFactor":
                    key = "mutationProbability"
                property_name = key + 'Value'
                key = key[0].upper() + key[1:]

                uri_parameter = URIRef(opt + 'Parameter_' + key)
                uri_parameter_value = URIRef(opt + 'ParameterValue_' + key + '_' + value)
                rdf.add( (uri_parameter_value, RDF.type, opt['ParameterValue']) )
                rdf.add( (uri_parameter_value, opt.valueOfParameter, uri_parameter) )
                rdf.add( (uri_experiment, opt.parameterValue, uri_parameter_value) )
                rdf.add( (uri_experiment, opt.using, uri_parameter) )

                value, type_ = get_type(value)
                rdf.add( (uri_parameter_value, opt[property_name], Literal(value, datatype=XSD[type_])) )


    # Store resulting ontology to disk
    with open(output_file + '.rdf', 'w+') as f:
        f.write(rdf.serialize(format='nt11').replace(
                '"nan"^^<http://www.w3.org/2001/XMLSchema#double>',
                '"NaN"^^<http://www.w3.org/2001/XMLSchema#double>'
            ) # This replace can't be done before because the Literal conversions reverts it back to python's nan)
        )