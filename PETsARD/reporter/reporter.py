from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Optional
import re

import pandas as pd

from PETsARD.error import ConfigError, UnexecutedError, UnsupportedMethodError


class ReporterMap():
    """
    Mapping of Reporter.
    """
    SAVE_DATA:   int = 10
    SAVE_REPORT: int = 11

    @classmethod
    def map(cls, method: str) -> int:
        """
        Get suffixes mapping int value

        Args:
            method (str): reporting method
        """
        try:
            return cls.__dict__[method.upper()]
        except KeyError:
            raise UnsupportedMethodError


class ReporterSaveReportMap():
    """
    Mapping of ReportSaveReport.
    """
    GLOBAL:     int = 1
    COLUMNWISE: int = 2
    PAIRWISE:   int = 3

    @classmethod
    def map(cls, granularity: str) -> int:
        """
        Get suffixes mapping int value

        Args:
            granularity (str): reporting granularity
        """
        try:
            return cls.__dict__[granularity.upper()]
        except KeyError:
            raise UnsupportedMethodError


class Reporter:
    """
    A class that represents a reporter.
    """

    def __init__(self, method: str, **kwargs):
        """
        Args:
            method (str): The method used for reporting.
            **kwargs: Additional configuration parameters.
                - All Reporter
                    - output (str, optional):
                        The output filename prefix for the report. Default is 'PETsARD'.
                - ReporterSaveData
                    - source (Union[str, List[str]]): The source of the data.
                - ReporterSaveReport
                    - granularity (str): The granularity of reporting.
                        It should be one of 'global', 'columnwise', or 'pairwise'.
                        Case-insensitive.
                    - eval (str | List[str], optional):
                        The evaluation method used for reporting.

        Attributes:
            config (dict): A dictionary containing the configuration parameters.
            reporter (object): An object representing the specific reporter based on the method.
            report_data (dict): A dictionary containing the data for the report.
        """
        self.config = kwargs
        self.config['method'] = method.lower()
        self.reporter = None
        self.report_data: dict = {}

        method_code: int = ReporterMap.map(self.config['method'])
        self.config['method_code'] = method_code
        if method_code == ReporterMap.SAVE_DATA:
            self.reporter = ReporterSaveData(config=self.config)
        elif method_code == ReporterMap.SAVE_REPORT:
            self.reporter = ReporterSaveReport(config=self.config)
        else:
            raise UnsupportedMethodError

    def create(self, data: dict) -> None:
        """
        Creates a report using the specified data.

        Args:
            data (dict): The data used for creating the report.
        """
        self.reporter.create(data=data)
        self.report_data = self.reporter.report_data

    def report(self) -> None:
        """
        Generates and saves the report.
        """
        self.reporter.report()


class ReporterBase(ABC):
    """
    Base class for reporting data.
    """
    SAVE_REPORT_AVAILABLE_MODULE: list = ['Evaluator', 'Describer']

    def __init__(self, config: dict):
        """
        Args:
            config (dict): Configuration settings for the report.
                - method (str): The method used for reporting.
                - output (str, optional): The output filename prefix for the report.
                    Default is 'PETsARD'.

        Attributes:
            config (dict): Configuration settings for the report.
            report_data (dict): Data for the report.
        """
        self.config: dict = config
        if 'method' not in self.config:
            raise ConfigError
        if not isinstance(self.config.get('output'), str) \
                or not self.config['output']:
            self.config['output'] = 'PETsARD'
        self.report_data: dict = {}

    @abstractmethod
    def create(self, data: dict) -> None:
        """
        Abstract method for creating the report.

        Args:
            data (dict): The data used for creating the report.
        """
        raise NotImplementedError

    @abstractmethod
    def report(self) -> None:
        """
        Abstract method for reporting the data.
        """
        raise NotImplementedError

    def _save(self, data: pd.DataFrame, full_output: str) -> None:
        """
        Save the data to a CSV file.

        Args:
            data (pd.DataFrame): The data to be saved.
            full_output (str): The full output path for the CSV file.
        """
        print(f"Now is {full_output} save to csv...")
        data.to_csv(
            path_or_buf=f"{full_output}.csv",
            index=False,
            encoding='utf-8'
        )


class ReporterSaveData(ReporterBase):
    """
    Save raw/processed data to file.
    """

    def __init__(self, config: dict):
        """
        Args:
            config (dict): The configuration dictionary.
                - method (str): The method used for reporting.
                - output (str, optional): The output filename prefix for the report.
                    Default is 'PETsARD'.
                - source (str | List[str]): The source of the data.

        Raises:
            ConfigError: If the 'source' key is missing in the config
                or if the value of 'source' is not a string or a list of strings.
        """
        super().__init__(config)

        # source should be string or list of string: Union[str, List[str]]
        if 'source' not in self.config:
            raise ConfigError
        elif not isinstance(self.config['source'], (str, list)) \
            or (isinstance(self.config['source'], list)
                and not all(isinstance(item, str) for item in self.config['source'])
                ):
            raise ConfigError

        # convert source to list if it is string
        if isinstance(self.config['source'], str):
            self.config['source'] = [self.config['source']]

    def create(self, data: dict) -> None:
        """
        Creates the report data.

        Args:
            data (dict): The data dictionary. Gerenrating by ReporterOperator.set_input()
                The key is the full index tuple of the source,
                    format is (module_name, experiment_name, ), and concat together. e.g.
                    ('Loader', 'default'),
                    ('Loader', 'default', 'Preprocessor', 'default')
                    If there's multiple result in the Operator, e.g. EvaluatorOperator,
                    Their expeirment name will add postfix "_[xxx]" to distinguish. e.g.
                    (..., 'Evaluator', 'default_[global]')
                The value is the data of the source.

        Raises:
            ConfigError: If the index tuple is not an even number.
        """
        # last 1 of index shoulde remove postifx "_[xxx]" to match source
        pattern = re.compile(r'_(\[[^\]]*\])$')
        for index, df in data.items():
            # check if last 2 element of index in source
            last_module_expt_name = [index[-2], re.sub(pattern, '', index[-1])]
            if any(item in self.config['source'] for item in last_module_expt_name):
                # index tuple should be even number
                if len(index) % 2 != 0:
                    raise ConfigError

                full_expt = '_'.join([
                    f"{index[i]}[{index[i+1]}]"
                    for i in range(0, len(index), 2)
                ])
                self.report_data[full_expt] = df

    def report(self) -> None:
        """
        Generates the report.

        Notes:
            Some of the data may be None, such as Evaluator.get_global/columnwise/pairwise. These will be skipped.
        """
        for expt_name, df in self.report_data.items():
            # Some of the data may be None.
            #   e.g. Evaluator.get_global/columnwise/pairwise
            #   just skip it
            if df is None:
                continue

            # PETsARD_{expt_name}
            full_output = f"{self.config['output']}_{expt_name}"
            self._save(data=df, full_output=full_output)


class ReporterSaveReport(ReporterBase):
    """
    Save evaluating/describing data to file.
    """

    def __init__(self, config: dict):
        """
        Args:
            config (dict): The configuration dictionary.
                - method (str): The method used for reporting.
                - output (str, optional): The output filename prefix for the report.
                    Default is 'PETsARD'.
                - granularity (str): The granularity of reporting.
                    It should be one of 'global', 'columnwise', or 'pairwise'.
                    Case-insensitive.
                - eval (str | List[str], optional):
                    The evaluation experiment name for export reporting.
                    Case-sensitive. Default is None

        Raises:
            ConfigError: If the 'source' key is missing in the config
                or if the value of 'source' is not a string or a list of strings.
        """
        super().__init__(config)

        # granularity should be whether global/columnwise/pairwise
        if 'granularity' not in self.config:
            raise ConfigError
        if not isinstance(self.config['granularity'], str):
            raise ConfigError
        self.config['granularity'] = self.config['granularity'].lower()
        granularity_code = ReporterSaveReportMap.map(self.config['granularity'])
        if granularity_code not in [
            ReporterSaveReportMap.GLOBAL,
            ReporterSaveReportMap.COLUMNWISE,
            ReporterSaveReportMap.PAIRWISE
        ]:
            raise ConfigError
        self.config['granularity_code'] = granularity_code

        # set eval to None if not exist,
        #   otherwise verify it should be str or List[str]
        eval = self.config.get('eval')
        if isinstance(eval, str):
            eval = [eval]
        if not isinstance(eval, list)\
            or not all(isinstance(item, str) for item in eval):
            if eval is not None:
                raise ConfigError
        self.config['eval'] = eval

    def create(self, data: dict = None) -> None:
        """
        Creating the report data by checking is experiment name of Evaluator exist.

        Args:
            data (dict): The data dictionary. Gerenrating by ReporterOperator.set_input()
                - The key is the full index tuple of the source,
                    format is (module_name, experiment_name, ), and concat together. e.g.
                    ('Loader', 'default'),
                    ('Loader', 'default', 'Preprocessor', 'default')
                    If there's multiple result in the Operator, e.g. EvaluatorOperator,
                    Their expeirment name will add postfix "_[xxx]" to distinguish. e.g.
                    (..., 'Evaluator', 'default_[global]')
                  The value is the data of the source.
                - also the keys exist_report (dict, optional): The existing report data.
                    The key is the full evaluation experiment name: "{eval}_[{granularity}]"
                    The value is the data of the report, pd.DataFrame.

        Attributes:
            - report_data (dict): Data for the report.
                - Reporter (dict): The report data for the reporter.
                    - full_expt_name (str): The full experiment name.
                    - expt_name (str): The experiment name.
                    - granularity (str): The granularity of the report.
                    - report (pd.DataFrame): The report data.
        """
        full_expt_name: str = ''
        eval_expt_name: str = ''
        eval: Optional[str] = self.config['eval']
        granularity: str = self.config['granularity'].lower()

        report_data: dict = {}
        rpt_data: pd.DataFrame = None
        exist_report: Optional[dict] = None

        if 'exist_report' in self.config:
            exist_report = self.config['exist_report']
            del self.config['exist_report']

        for idx_tuple, rpt_data in data.items():
            # found latest key pairs is Evaluator/Describer
            if idx_tuple[-2] not in self.SAVE_REPORT_AVAILABLE_MODULE:
                continue

            # specifiy experiment name
            #   match the expt_name "{eval}_[{granularity}]"
            if eval_expt_name != f"{eval}_[{granularity}]":
                continue

            if rpt_data is None:
                print(
                    f"There's no {granularity} granularity report in {eval}. "
                    f"Nothing collect."
                )
                return
            else:
                rpt_data = deepcopy(rpt_data)

                full_expt_name: str = '_'.join([
                    f"{idx_tuple[i]}[{idx_tuple[i+1]}]"
                    for i in range(0, len(idx_tuple), 2)
                ])
                report_data['full_expt_name'] = full_expt_name
                report_data['eval_expt_name'] = eval_expt_name
                report_data['expt_name'] = eval
                report_data['granularity'] = granularity

                # reset index to represent column
                granularity_code = self.config['granularity_code']
                if granularity_code == ReporterSaveReportMap.COLUMNWISE:
                    rpt_data = rpt_data.reset_index(drop=False)
                    rpt_data = rpt_data.rename(columns={'index': 'column'})
                elif granularity_code == ReporterSaveReportMap.PAIRWISE:
                    rpt_data = rpt_data.reset_index(drop=False)
                    rpt_data = rpt_data.rename(columns={
                        'level_0': 'column1',
                        'level_1': 'column2'
                    })

                # add full_expt_name as first column
                rpt_data.insert(0, 'full_expt_name', full_expt_name)

                # Row append if exist_report exist
                if exist_report is not None:
                    if eval_expt_name in exist_report:
                        exist_report_data = exist_report[eval_expt_name]
                        rpt_data = pd.concat(
                            [exist_report_data, rpt_data],
                            axis=0
                        )
                report_data['report'] = deepcopy(rpt_data)

                # only one matched Evaluator/Describer should in the Status.status
                break

        self.report_data['Reporter'] = report_data

    def report(self) -> None:
        """
        Generates a report based on the provided report data.
            The report is saved to the specified output location.
        """
        if 'Reporter' not in self.report_data:
            raise UnexecutedError

        if 'eval_expt_name' not in self.report_data['Reporter']:
            # no {granularity} granularity report in {eval}
            return

        eval_expt_name: str = self.report_data['Reporter']['eval_expt_name']

        # PETsARD[Report]_{eval_expt_name}
        full_output = f"{self.config['output']}[Report]_{eval_expt_name}"
        self._save(
            data=self.report_data['Reporter']['report'],
            full_output=full_output
        )

