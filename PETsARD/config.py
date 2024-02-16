from copy import deepcopy
import queue
from typing import Tuple
import yaml

from PETsARD.operator import (
    Operator,
    LoaderOperator,
    SplitterOperator
)


class Sequence:
    """
    Initializes a sequence of modules for an experiment.
    """

    def __init__(self, sequence: list = None):
        """  
        Args:
            sequence (list, optional):
                The user defined sequence of modules in the experiment.

        Attributes:
            default_sequence (list):
                The default sequence of modules.
            sequence (list):
                The sequence of modules for the experiment.
        """
        self.default_sequence: list = [
            'Loader', 'Splitter'
        ]

        self.sequence: list = self.default_sequence if sequence is None else sequence


class Config:
    """
    The config of experiment for executor to read.

    Config file should follow specific format:
    ...
    - {module name}
        - {task name}
            - {module parameter}: {value}
    ...
    task name is assigned by user.
    """

    def __init__(self, filename: str, sequence: list = None):
        """
        Args:
            filename (str)
                The filename of config file.
            sequence (list. Optional):
                The user defined sequence of modules in the experiment.
        """
        self.config:      queue.Queue = queue.Queue()
        self.module_flow: queue.Queue = queue.Queue()
        self.expt_flow:   queue.Queue = queue.Queue()
        self.filename = filename
        self.yaml: dict = {}

        self.sequence: list = Sequence(sequence).sequence

        with open(self.filename, 'r') as yaml_file:
            self.yaml = yaml.safe_load(yaml_file)

        if 'Splitter' in self.yaml:
            self.yaml['Splitter'] = self._splitter_handler(
                deepcopy(self.yaml['Splitter'])
            )

        self.config, self.module_flow, self.expt_flow = self._set_flow()

    def _set_flow(self) -> Tuple[queue.Queue, queue.Queue, queue.Queue]:
        """
        Populate queues with module operators.

        Returns:
            flow (queue.Queue):
                Queue containing the operators in the order they were traversed.
            module_flow (queue.Queue):
                Queue containing the module names corresponding to each operator.
            expt_flow (queue.Queue):
                Queue containing the experiment names corresponding to each operator.
        """
        flow:        queue.Queue = queue.Queue()
        module_flow: queue.Queue = queue.Queue()
        expt_flow:   queue.Queue = queue.Queue()

        def _set_flow_dfs(modules):
            """
            Depth-First Search (DFS) algorithm
                for traversing the sequence of modules recursively.
            """
            if not modules:
                return

            module = modules[0]
            remaining_modules = modules[1:]

            if module in self.yaml:
                for expt_name, expt_config in self.yaml[module].items():
                    flow.put(eval(f"{module}Operator(expt_config)"))
                    module_flow.put(module)
                    expt_flow.put(expt_name)
                    _set_flow_dfs(remaining_modules)

        _set_flow_dfs(self.sequence)
        return flow, module_flow, expt_flow

    def _splitter_handler(self, config: dict) -> dict:
        """
        Transforms and expands the Splitter configuration for each specified 'num_samples',
            creating unique entries with a new experiment name format '{expt_name}_0n|NN}."

        Args:
            config (dict):
                The original Splitter configuration.

        Returns:
            (dict):
                Transformed and expanded configuration dictionary.
        """
        transformed_config: dict = {}
        for expt_name, expt_config in config.items():
            num_samples = expt_config.get('num_samples', 1)
            iter_expt_config = deepcopy(expt_config)
            iter_expt_config['num_samples'] = 1

            num_samples_str = str(num_samples)
            zero_padding = len(num_samples_str)
            for n in range(num_samples):
                # fill zero on n
                formatted_n = f"{n+1:0{zero_padding}}"
                iter_expt_name = f"{expt_name}_[{formatted_n}|{num_samples}]"
                transformed_config[iter_expt_name] = iter_expt_config
        return transformed_config


class Status:
    """
    Managing the status and results of modules in Executor.

    Methods:
        put(module, expt, operator):
            Add module status and operator to the status dictionary.

        get_result(module, tag=None):
            Retrieve the result of a specific module, optionally specifying a tag.

        get_full_expt():
            Retrieve a dictionary of module names and their corresponding experiment names.

        get_exist_index():
            Retrieve the list of unique training indices generated by 'Splitter' modules.

    """

    def __init__(self, sequence: list = None):
        """
        Args:
            sequence (list. Optional):
                The user defined sequence of modules in the experiment.

        Attributes:
            sequence (list):
                The sequence of modules in the experiment.
            status (dict):
                A dictionary containing module Operators.
            exist_index (list):
                A list of unique already training indices generated by 'Splitter' modules.
        """

        self.sequence = Sequence(sequence).sequence
        self.status: dict = {}
        if 'Splitter' in self.sequence:
            self.exist_index: list = []

    def put(self, module: str, expt: str, operator: Operator):
        """
        Add module status and operator to the status dictionary.
            Update exist_index when put Splitter.

        Args
            module (str):
                Current module name.
            expt (str):
                Current experiment name.
            operator (Operator):
                Current Operator.
        """
        temp = {}
        temp['expt'] = expt
        temp['operator'] = operator
        self.status[module] = deepcopy(temp)

        if module == 'Splitter':
            curr_exist_index: list = [
                idx for value in operator.splitter.index.values()
                for idx in value['train'] 
            ]
            self.exist_index = list(set(self.exist_index + curr_exist_index))

    def get_result(self, module: str, tag: str = None):
        """
        Retrieve the result of a specific module, optionally specifying a tag.

        Args
            tag (str. Optional)
                Result tag for Splitter.
        """
        return self.status[module]['operator'].get_result(tag=tag)

    def get_full_expt(self):
        """
        Retrieve a dictionary of module names and their corresponding experiment names.
        """
        return {module: self.status[module]['expt'] for module in self.sequence}

    def get_exist_index(self):
        """
        Retrieve the list of unique training indices generated by 'Splitter' modules.
        """
        return self.exist_index