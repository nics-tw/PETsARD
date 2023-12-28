import numpy as np
import pandas as pd
from ..Error import UnfittedError

from copy import deepcopy


class Missingist:
    def __init__(self):
        self._is_fitted = False
        self.na_percentage = None
        self.rng = np.random.default_rng()

    def set_na_percentage(self, na_percentage: float = 0.0):
        if na_percentage > 1.0 or na_percentage < 0.0:
            raise ValueError('Invalid NA percentage. It should be between 0.0 and 1.0.')
        
        self.na_percentage = na_percentage

    def fit(self, data):
        self._fit(data)

        self._is_fitted = True

    def transform(self, data):
        # Check the object is fitted
        if not self._is_fitted:
            raise UnfittedError('The object is not fitted. Use .fit() first.')
        
        return self._transform(data)
    
    def inverse_transform(self, data):
        """
        Insert NA into the data to have the same pattern with the original data.

        Input:
            data (pd.Series): The data needed to be transformed inversely.

        Output:
            (np.ndarray): The inverse transformed data.
        """
        # Check the object is fitted
        if not self._is_fitted:
            raise UnfittedError('The object is not fitted. Use .fit() first.')
        
        _na_mask = self.rng.random(data.shape[0])
        _na_mask = _na_mask < self.na_percentage
        _col_data = deepcopy(data)
        _col_data[_na_mask] = np.nan

        return _col_data

class Missingist_Mean(Missingist):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_mean = None

    def _fit(self, data):
        """
        Gather information for transformation and reverse transformation.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            None
        """

        self.data_mean = data.mean()

    def _transform(self, data):
        """
        Fill NA with mean.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            (pd.Series): The transformed data.
        """

        return data.fillna(self.data_mean)
    
    def _inverse_transform(self, data):
        pass # Redundant
    
class Missingist_Median(Missingist):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_median = None

    def _fit(self, data):
        """
        Gather information for transformation and reverse transformation.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            None
        """

        self.data_median = data.median()

    def _transform(self, data):
        """
        Fill NA with median.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            (pd.Series): The transformed data.
        """

        return data.fillna(self.data_median)
    
    def _inverse_transform(self, data):
        pass # Redundant
    
class Missingist_Simple(Missingist):
    def __init__(self, value=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_value = value

    def _fit(self, data):
        pass # Redundant

    def _transform(self, data):
        """
        Fill NA with median.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            (pd.Series): The transformed data.
        """

        return data.fillna(self.data_value)
    
    def _inverse_transform(self, data):
        pass # Redundant

class Missingist_Drop(Missingist):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_backup = None # for restoring data

    def _fit(self, data):
        pass # Redundant

    def _transform(self, data):
        """
        Mark the NA cells and store the original data.

        Input:
            data (pd.Series): The data needed to be transformed.

        Output:
            (np.ndarray): The filter marking the NA cells.
        """
        self.data_backup = data

        return data.isna().values.ravel()
    
    def _inverse_transform(self, data):
        pass # Redundant