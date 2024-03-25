import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor,\
        RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.cluster import KMeans
from sklearn.metrics import f1_score, silhouette_score
from tqdm import tqdm

from PETsARD.error import ConfigError, UnsupportedMethodError
from PETsARD.evaluator.evaluator_base import EvaluatorBase
from PETsARD.util.safe_round import safe_round
import re

class AutoMLMap():
    """
    map of AutoML
    """
    REGRESSION:   int = 1
    CLASSIFICATION: int = 2
    CLUSTER: int = 3

    @classmethod
    def map(cls, method: str) -> int:
        """
        Get suffixes mapping int value

        Args:
            method (str): evaluating method

        Return:
            (int): The method code.
        """
        try:
            return cls.__dict__[
                re.sub(r"^automl-", "", method).upper()
            ]
        except KeyError:
            raise UnsupportedMethodError

class AutoML(EvaluatorBase):
    """
    Interface class for AutoML Models.

    AutoML is a class that evaluating dataset utility.

    Args:
        config (dict): A dictionary containing the configuration settings.
            - method (str): The method name of how you evaluating data, which
            is downstream task of the data.
            - target (str): The target column of the data. Required for
            regression and classification. Ignored for clustering. Should be
            a numerical column for regression.
            - n_splits (int): The parameter for k-fold cross validation. Should
            be greater than 1.
    """

    def __init__(self, config: dict):
        if 'method' not in config:
            raise ConfigError

        super().__init__(config=config)
        self.data: dict = {}

        self.ml = ML(self.config)

    def create(self, data):
        """
        Create a worker and send the data to the worker.

        Args:
            data (dict): The data to be described. The keys should be 'ori'
            and 'syn, and the value should be a pandas DataFrame.
        """
        self.data = data

        self.ml.create(self.data)

    def eval(self):
        """
        Evaluate the data with the method given in the config.
        """
        self.ml.eval()

        self.result = self.ml.result

    def get_global(self):
        """
        Get the global result of the evaluation.
        """
        return self.ml.get_global()

    def get_columnwise(self):
        """
        Get the column-wise result of the evaluation. Dummy method.
        """
        return self.ml.get_columnwise()

    def get_pairwise(self):
        """
        Get the pair-wise result of the evaluation. Dummy method.
        """
        return self.ml.get_pairwise()


class ML:
    """
    Train and evaluate the models based on the original data and the synthetic
    data. The worker of AutoML.

    Args:
        config (dict): A dictionary containing the configuration settings.
            - method (str): The method name of how you evaluating data, which
            is downstream task of the data.
            - target (str): The target column of the data. Required for
            regression and classification. Ignored for clustering. Should be
            a numerical column for regression.
            - n_splits (int): The parameter for k-fold cross validation. Should
            be greater than 1.
    """

    def __init__(self, config: dict):
        self.config: dict = config
        self.config['method_code'] = AutoMLMap.map(config['method'])

        self.result_ori: dict = {}
        self.result_syn: dict = {}

        # store the aggregated result
        self.result: dict = {}

        self.n_splits = self.config.get('n_splits', 5)

        self.data_content: pd.DataFrame = None

    def create(self, data):
        """
        Store the data in the instance.

        Args:
            data (pd.DataFrame): The data to be trained on.
        """
        self.data_content = data

    def eval(self):
        """
        Data preprocessing and model fitting and evaluation.

        Data preprocessing process: remove missing values, one-hot encoding for
        categorical variables, and normalisation.
        """

        data_ori = self.data_content['ori']
        data_syn = self.data_content['syn']

        # Data preprocessing
        data_ori = data_ori.dropna()
        data_syn = data_syn.dropna()

        if 'target' in self.config:
            target = self.config['target']
            target_ori = data_ori[target].values
            data_ori = data_ori.drop(columns=[target])
            target_syn = data_syn[target].values
            data_syn = data_syn.drop(columns=[target])
        else:
            if self.config['method_code'] != AutoMLMap.CLUSTER:
                raise ConfigError

        data_ori = pd.get_dummies(data_ori, drop_first=True)
        data_syn = pd.get_dummies(data_syn, drop_first=True)

        if self.config['method_code'] == AutoMLMap.REGRESSION:
            self.result_ori = self._regression(data_ori, target_ori,
                                               self.n_splits)
            self.result_syn = self._regression(data_syn, target_syn,
                                               self.n_splits)
        elif self.config['method_code'] == AutoMLMap.CLASSIFICATION:
            self.result_ori = self._classification(data_ori, target_ori,
                                                   self.n_splits)
            self.result_syn = self._classification(data_syn, target_syn,
                                                   self.n_splits)
        elif self.config['method_code'] == AutoMLMap.CLUSTER:
            self.result_ori = self._cluster(data_ori, self.n_splits)
            self.result_syn = self._cluster(data_syn, self.n_splits)

        self.result = {'ori': self.result_ori, 'syn': self.result_syn}


    def _regression(self, data, target, n_splits):
        """
        Regression model fitting and evaluation.
        The models used are linear regression, random forest,
        and gradient boosting.

        For the robustness of the results, the model is trained
        and evaluated 5 times, and the average of the results
        is used as the final result.

        To prevent the data leakage, the normalisation is done inside the loop.

        The metric used for evaluation is R^2.

        Args:
            data (pd.DataFrame): The data to be fitted.
            target (str): The target column of the data.
            n_splits (int): The parameter for k-fold cross validation. Should
            be greater than 1.

        Returns:
            result (dict): The result of the evaluation.
        """
        result = {
            'linear_regression': [],
            'random_forest': [],
            'gradient_boosting': []
        }

        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

        for train_index, test_index in tqdm(kf.split(data, target),
                                            desc='Regression',
                                            total=n_splits):
            data_train, data_test = data.iloc[train_index, :], \
                data.iloc[test_index, :]
            target_train, target_test = target[train_index], \
                target[test_index]

            ssx = StandardScaler()
            data_train = ssx.fit_transform(data_train)
            data_test = ssx.transform(data_test)

            ssy = StandardScaler()
            target_train = ssy.fit_transform(target_train.reshape(-1, 1)).ravel()
            target_test = ssy.transform(target_test.reshape(-1, 1)).ravel()

            lr = LinearRegression()
            rf = RandomForestRegressor(random_state=42)
            gb = GradientBoostingRegressor(random_state=42)

            lr.fit(data_train, target_train)
            rf.fit(data_train, target_train)
            gb.fit(data_train, target_train)

            result['linear_regression'].append(lr.score(data_test, target_test))
            result['random_forest'].append(rf.score(data_test, target_test))
            result['gradient_boosting'].append(gb.score(data_test, target_test))

        return result

    def _classification(self, data, target, n_splits):
        """
        Classification model fitting and evaluation.
        The models used are logistic regression, SVC, random forest,
        and gradient boosting.

        For the robustness of the results, the model is trained
        and evaluated 5 times, and the average of the results
        is used as the final result.

        To prevent the data leakage, the normalisation is done inside the loop.

        The metric used for evaluation is f1 score.

        Args:
            data (pd.DataFrame): The data to be fitted.
            target (str): The target column of the data.
            n_splits (int): The parameter for k-fold cross validation. Should
            be greater than 1.

        Returns:
            result (dict): The result of the evaluation.
        """
        result = {
            'logistic_regression': [],
            'svc': [],
            'random_forest': [],
            'gradient_boosting': []
        }

        kf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        for train_index, test_index in tqdm(kf.split(data, target),
                                            desc='Classification',
                                            total=n_splits):
            data_train, data_test = data.iloc[train_index, :],\
                data.iloc[test_index, :]
            target_train, target_test = target[train_index], \
                target[test_index]

            ss = StandardScaler()
            data_train = ss.fit_transform(data_train)
            data_test = ss.transform(data_test)

            lr = LogisticRegression(random_state=42)
            svc = SVC(random_state=42)
            rf = RandomForestClassifier(random_state=42)
            gb = GradientBoostingClassifier(random_state=42)

            lr.fit(data_train, target_train)
            svc.fit(data_train, target_train)
            rf.fit(data_train, target_train)
            gb.fit(data_train, target_train)

            result['logistic_regression'].append(f1_score(target_test,
                                                          lr.predict(data_test),
                                                          average='micro'))
            result['svc'].append(f1_score(target_test,
                                          svc.predict(data_test),
                                          average='micro'))
            result['random_forest'].append(f1_score(target_test,
                                                    rf.predict(data_test),
                                                    average='micro'))
            result['gradient_boosting'].append(f1_score(target_test,
                                                        gb.predict(data_test),
                                                        average='micro'))

        return result

    def _cluster(self, data, n_splits):
        """
        Clustering model fitting and evaluation.
        The models used are KMeans with different number of clusters.

        For the robustness of the results, the model is trained
        and evaluated 5 times, and the average of the results
        is used as the final result.

        To prevent the data leakage, the normalisation is done inside the loop.

        The metric used for evaluation is silhouette score.

        Args:
            data (pd.DataFrame): The data to be fitted.
            n_splits (int): The parameter for k-fold cross validation. Should
            be greater than 1.

        Returns:
            result (dict): The result of the evaluation.
        """
        result = {
            'KMeans_cluster4': [],
            'KMeans_cluster5': [],
            'KMeans_cluster6': []
        }

        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

        for train_index, test_index in tqdm(kf.split(data),
                                            desc='Clustering',
                                            total=n_splits):
            data_train, data_test = data.iloc[train_index, :], \
                data.iloc[test_index, :]

            ss = StandardScaler()
            data_train = ss.fit_transform(data_train)
            data_test = ss.transform(data_test)

            k4 = KMeans(random_state=42, n_clusters=4, n_init='auto')
            k5 = KMeans(random_state=42, n_clusters=5, n_init='auto')
            k6 = KMeans(random_state=42, n_clusters=6, n_init='auto')

            k4.fit(data_train)
            k5.fit(data_train)
            k6.fit(data_train)

            result['KMeans_cluster4'].append(
                silhouette_score(data_test, k4.predict(data_test))
            )
            result['KMeans_cluster5'].append(
                silhouette_score(data_test, k5.predict(data_test))
            )
            result['KMeans_cluster6'].append(
                silhouette_score(data_test, k6.predict(data_test))
            )

        return result

    def get_global(self) -> pd.DataFrame:
        """
        Get the global result of the evaluation.

        Returns:
            (pd.DataFrame): The global result of the evaluation.
        """
        syn_value = []

        for i in self.result_syn.values():
            syn_value += i

        ori_value = []

        for i in self.result_ori.values():
            ori_value += i

        normalise_range = 2 if self.config['method'] == 'cluster' else 1

        compare_df = pd.DataFrame({'ori_mean': safe_round(np.mean(ori_value)),
                                   'ori_std': safe_round(np.std(ori_value)),
                                   'syn_mean': safe_round(np.mean(syn_value)),
                                   'syn_std': safe_round(np.std(syn_value))},
                                   index=[0])

        compare_df['pct_change'] = safe_round((compare_df['syn_mean'] -
                                    compare_df['ori_mean']) /
                                    normalise_range) * 100

        return compare_df

    def get_columnwise(self) -> None:
        """
        Dummy method for the column-wise result of the evaluation.

        Returns:
            None: None for ML didn't have columnwise result.
        """
        return None

    def get_pairwise(self) -> None:
        """
        Dummy method for the pair-wise result of the evaluation.

        Returns:
            None: None for ML didn't have pairwise result.
        """
        return None