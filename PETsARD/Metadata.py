import pandas as pd


class Metadata:
    def __init__(self):
        self.metadata = None

    def build_metadata(self, data: pd.DataFrame) -> None:
        """
        Create metadata from the data and infer data types from the metadata, which is used for generating config and `to_sdv` method.

        The infer data types can be one of the following: 'numerical', 'categorical', 'datetime', and 'object'.

        Args:
            data (pd.DataFrame): The dataframe used for building metadata.

        Return:
            None
        """
        self._check_dataframe_valid(data)

        metadata = {'metadata_col': None, 'metadata_global': {}}

        metadata['metadata_global']['row_num'] = data.shape[0]
        metadata['metadata_global']['col_num'] = data.shape[1]
        metadata['metadata_global']['na_percentage'] = data.isna()\
            .any(axis=1).mean()

        # create type and na_percentage keys and values automatically
        metadata_df = data.dtypes.reset_index(name='dtype')\
            .merge(data.isna().mean(axis=0).reset_index(name='na_percentage'),
                   on='index').set_index('index')

        # infer dtypes
        metadata_df['infer_dtype'] = metadata_df['dtype']\
            .apply(self._convert_dtypes)

        metadata['metadata_col'] = metadata_df.to_dict('index')

        self.metadata = metadata

    def _check_dataframe_valid(self, data: pd.DataFrame) -> None:
        """
        Check the validity of dataframe.

        Args:
            data (pd.DataFrame): The dataframe to be checked.

        Return:
            None
        """
        if type(data) != pd.DataFrame:
            raise TypeError('Data should be a pd.DataFrame.')

        if data.shape[0] <= 0:
            raise ValueError(
                'There should be at least one row in the dataframe.')

        if data.shape[1] <= 0:
            raise ValueError(
                'There should be at least one column in the dataframe.')

    def _convert_dtypes(self, dtype: type) -> str:
        """
        Auxiliary function for inferring dtypes.

        Args:
            dtype (type): The data type from the data.

        Return:
            (str): The inferred data type.
        """
        if dtype is None:
            raise ValueError(f'{dtype} is invalid.')

        if pd.api.types.is_numeric_dtype(dtype):
            return 'numerical'
        elif isinstance(dtype, pd.CategoricalDtype):
            return 'categorical'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'datetime'
        elif pd.api.types.is_object_dtype(dtype):
            return 'object'
        else:
            raise ValueError(f'{dtype} is invalid.')

    def to_sdv(self) -> dict:
        """
        Transform the metadata to meet the format of SDV.

        Args:
            None

        Return:
            sdv_metadata (dict): The metadata in SDV metadata format.
        """
        if self.metadata is None:
            raise ValueError(
                'Please use `build_metadata()` to construct the metadata first.')

        sdv_metadata = {'columns': {}}

        for col, val in self.metadata['metadata_col'].items():
            sdtype = val.get('infer_dtype')

            if sdtype is None or sdtype == 'object':
                raise ValueError(f'{col} is in invalid type {sdtype}.')

            sdv_metadata['columns'][col] = {'sdtype': sdtype}

        return sdv_metadata