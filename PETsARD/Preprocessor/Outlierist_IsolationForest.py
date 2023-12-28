from .Outlierist import Outlierist
from pandas import to_datetime
from pandas.api.types import is_datetime64_any_dtype
from sklearn.ensemble import IsolationForest

class Outlierist_IsolationForest(Outlierist):
    def __init__(self, df_data, **kwargs):
        super().__init__(df_data, **kwargs)

    def handle(self):
        """
        Outlier - Isolation Forest method.
        Drop the samples identified as outliers by Isolation Forest.

        ...
        Method:
            Outlierist_IsolationForest(pandas.DataFrame)
            Returns:
                pandas.DataFrame: A pandas DataFrame
                    containing drop outlier data, and already re-indexing.
        ...

        Args:

            df_data (pandas.DataFrame):
                The pandas DataFrame which might included missing value.

            outlier_columns_action (list ,optional):
                Specifies the columns for check outlier value.
        """

        _row_ori = self.df_data.shape[0]
        _digits_row_ori = len(str(_row_ori))
        
        transformed_data = self.df_data.copy()

        for _col_name in self.outlier_columns_action:
            _col_data = transformed_data[_col_name]
            if is_datetime64_any_dtype(_col_data):

                _col_data_timestamp = to_datetime(
                    _col_data).view(int) / 10**9
                
                transformed_data[_col_name] = _col_data_timestamp

        isof = IsolationForest()

        outlier_vector = isof.fit_predict(transformed_data[self.outlier_columns_action])



        _row_drop_ttl = sum(outlier_vector == -1)
        if _row_drop_ttl == 0:
            print(f'Preprocessor - Outlierist (Isolation Forest): None of rows have been dropped.')
        else:
            print(
                f'Preprocessor - Outlierist (Isolation Forest): Totally Dropped {_row_drop_ttl: >{_digits_row_ori}} in {_row_ori} rows.')

        self.df_data = self.df_data.loc[outlier_vector == 1].reset_index(drop=True)

        return self.df_data