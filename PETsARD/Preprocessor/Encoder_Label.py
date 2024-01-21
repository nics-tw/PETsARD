from pandas.api.types import CategoricalDtype
from sklearn.preprocessing import LabelEncoder

from PETsARD.Preprocessor.Encoder import Encoder


class Encoder_Label(Encoder):
    def __init__(self, df_data, **kwargs):
        super().__init__(df_data, **kwargs)

    def handle(self):
        """
        Encoder - Label Encoder.
        Encoding categorical data in DataFrame based on their labels,
        value between 0 to n_classes-1.
        Use sklearn.preprocessing.LabelEncoder.

        ...
        Method:
            Encoder_Label(pandas.DataFrame)
            Returns:
                pandas.DataFrame: A pandas DataFrame
                    containing labelized data.
        ...

        Args:

            df_data (pandas.DataFrame):
                The pandas DataFrame which might included missing value.

            encoder_columns_action (list ,optional):
                Specifies the columns for convert by encoder.
        """
        self.dict_encoder = {}
        digits_longest_colname = len(
            max(self.encoding_columns_action, key=len)
        )
        max_max_code = 0
        arr_print = []
        for col_name in self.encoding_columns_action:
            col_data = self.df_data[col_name]
            if isinstance(col_data.dtype, CategoricalDtype):
                self.dict_encoder[col_name] = LabelEncoder()
                self.df_data[col_name] = \
                    self.dict_encoder[col_name].fit_transform(col_data)

                max_code = len(self.dict_encoder[col_name].classes_)-1
                max_max_code = max(max_max_code, max_code)

                arr_print.append(
                    [f"Preprocessor - Encoder (Label): "
                        f"Column {col_name:<{digits_longest_colname}} "
                        f"been labelized from 0 to ",
                     max_code,
                     '.'
                     ]
                )

        # Label result with colname and max_label alignment. e.g.
        # Preprocessor - Encoder (Label):
        #     Column workclass
        #     been labelized from 0 to  8.
        arr_print = [
            f"{col1}{col2:>{len(str(max_max_code))}}{col3}"
            for col1, col2, col3 in arr_print
        ]
        print('\n'.join(arr_print))

        return self.df_data, self.dict_encoder
