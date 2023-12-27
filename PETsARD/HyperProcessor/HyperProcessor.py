from ..Processor.Encoder import *
from ..Processor.Missingist import *
from ..Processor.Outlierist import *
from ..Processor.Scaler import *
from .Mediator import *
from ..Error import *

# TODO - edit type in metadata to meet the standard of pandas
# TODO - add input and output types to all functions

class HyperProcessor:

    # object datatype indicates the unusual data,
    # passive actions will be taken in processing procedure

    _DEFAULT_MISSINGIST = {'numerical': Missingist_Mean, 
                           'categorical': Missingist_Drop,
                           'datetime': Missingist_Drop,
                           'object': Missingist_Drop}
    
    # TODO - add LOF and Isolation Forest as global config to outlierist
    
    _DEFAULT_OUTLIERIST = {'numerical': Outlierist_IQR,
                           'categorical': None,
                           'datatime': Outlierist_IQR,
                           'object': None}
    
    _DEFAULT_ENCODER = {'numerical': None,
                        'categorical': Encoder_Uniform,
                        'datetime': None,
                        'object': Encoder_Uniform}
    
    _DEFAULT_SCALER = {'numerical': Scaler_Standard,
                       'categorical': None,
                       'datetime': Scaler_Standard,
                       'object': None}
    
    _DEFAULT_SEQUENCE = ['missingist', 'outlierist', 'encoder', 'scaler']
    


    def __init__(self, metadata, config=None) -> None:
        self._check_metadata_valid(metadata=metadata)
        self._metadata = metadata

        # processing sequence
        self._sequence = None
        self._fitting_sequence = None
        self._is_fitted = False

        # deal with global transformation of missingist and outlierist
        self.mediator_missingist = None
        self.mediator_outlierist = None

        self._config = dict()

        if config is None:
            self._generate_config()
        else:
            self.set_config(config=config)

    def _check_metadata_valid(self, metadata):
        """
        Check whether the metadata contains the proper keys (metadata_col and metadata_global) for generating config.

        Input:
            metadata (dict): Metadata from the class Metadata or with the same format.

        Output:
            None
        """
        if not ('metadata_col' in metadata and 'metadata_global' in metadata):
            raise ValueError("'metadata_col' and 'metadata_global' should be in the metadata.")

    def _check_config_valid(self, config_to_check=None):
        """
        Check whether the config contains valid preprocessors. It checks the validity of column names, the validity of processor types (i.e., dict keys), and the validity of processor objects (i.e., dict values).

        Input:
            config (dict, default=None): Config generated by the class or with the same format.

        Output:
            None
        """
        if config_to_check is None:
            raise ValueError('A config should be passed.')

        # check the structure of config
        if type(config_to_check) != dict:
            raise TypeError('Config should be a dict.')

        # check the validity of processor types
        if not set(config_to_check.keys()).issubset({'missingist', 'outlierist', 'encoder', 'scaler'}):
            raise ValueError(f'Invalid config processor type in the input dict, please check the dict keys of processor types.')

        for processor, processor_class in {'missingist': Missingist, 'outlierist': Outlierist, 'encoder': Encoder, 'scaler': Scaler}.items():

            if config_to_check.get(processor, None) is None:
                continue
            
            if type(config_to_check[processor]) != dict:
                raise TypeError('The config in each processor should be a dict.')
            
            # check the validity of column names (keys)
            if not set(config_to_check[processor].keys()).issubset(set(self._metadata['metadata_col'].keys())):
                raise ValueError(f'Some columns in the input config {processor} are not in the metadata. Please check the config or metadata again.')

            for col in config_to_check[processor].keys():
                # check the validity of processor objects (values)
                obj = config_to_check[processor].get(col, None)

                if not(isinstance(obj, processor_class) or obj is None):
                    raise ValueError(f'{col} from {processor} contain(s) invalid processor object(s), please check them again.')
                    
    def _generate_config(self):
        """
        Generate config based on the metadata.

        Config structure: {processor_type: {col_name: processor_obj}}

        Input:
            None: The metadata is stored in the instance itself.

        Output:
            None: The config will be stored in the instance itself.
        """
        self._config = None # initialise the dict
        self._config = {'missingist': {},
                        'outlierist': {},
                        'encoder': {},
                        'scaler': {}}

        for col, val in self._metadata['metadata_col'].items():

            processor_dict = {'missingist': self._DEFAULT_MISSINGIST[val['type']]()\
                               if self._DEFAULT_MISSINGIST[val['type']] is not None else None,
                            'outlierist': self._DEFAULT_OUTLIERIST[val['type']]()\
                               if self._DEFAULT_OUTLIERIST[val['type']] is not None else None,
                            'encoder': self._DEFAULT_ENCODER[val['type']]()\
                               if self._DEFAULT_ENCODER[val['type']] is not None else None,
                            'scaler': self._DEFAULT_SCALER[val['type']]()\
                               if self._DEFAULT_SCALER[val['type']] is not None else None}
            
            for processor, obj in processor_dict.items():
                self._config[processor][col] = obj


    def get_config(self, col=[], print_config=False):
        """
        Get the config from the instance.

        Input:
            col (list): The columns the user want to get the config from. If the list is empty, all columns from the metadata will be selected.
            print_config (bool, default=False): Whether the result should be printed.

        Output:
            (dict): The config with selected columns.
        """
        get_col_list = []
        result_dict = {'missingist': {},
                       'outlierist': {},
                       'encoder': {},
                       'scaler': {}}

        if col:
            get_col_list = col
        else:
            get_col_list = list(self._metadata['metadata_col'].keys())

        if print_config:
            for processor in self._config.keys():
                print(processor)
                for colname in get_col_list:
                    print(f'    {colname}: {self._config[processor][colname].__class__}')
                    result_dict[processor][colname] = self._config[processor][colname]
        else:
            for processor in self._config.keys():
                for colname in get_col_list:
                    result_dict[processor][colname] = self._config[processor][colname]


        return result_dict

    def set_config(self, config):
        """
        Edit the whole config. To keep the structure of the config, it fills the unspecified preprocessors with None. To prevent from this, use update_config() instead.

        Input:
            config (dict): The dict with the same format as the config class.

        Output:
            None
        """
        self._check_config_valid(config_to_check=config)

        for processor, val in self._config.items():
            if processor not in config.keys():
                config[processor] = {}
            for col in val.keys():
                self._config[processor][col] = config[processor].get(col, None)

    def update_config(self, config):
        """
        Update part of the config.

        Input:
            config (dict): The dict with the same format as the config class.

        Output:
            None
        """
        self._check_config_valid(config_to_check=config)

        for processor, val in config.items():
            for col, obj in val.items():
                self._config[processor][col] = obj

    def fit(self, data, sequence=None):

        if sequence is None:
            self._sequence = self._DEFAULT_SEQUENCE
        else:
            self._check_sequence_valid(sequence)
            self._sequence = sequence

        self._fitting_sequence = self._sequence.copy()

        if 'missingist' in self._sequence:
            # if missingist is in the procedure, Mediator_Missingist should be in the queue right after the missingist
            self.mediator_missingist = Mediator_Missingist(self._config)
            self._fitting_sequence.insert(self._fitting_sequence.index('missingist')+1, self.mediator_missingist)
            print('Mediator_Missingist is created.')

        if 'outlierist' in self._sequence:
            # if outlierist is in the procedure, Mediator_Outlierist should be in the queue right after the outlierist
            self.mediator_outlierist = Mediator_Outlierist(self._config)
            self._fitting_sequence.insert(self._fitting_sequence.index('outlierist')+1, self.mediator_outlierist)
            print('Mediator_Outlierist is created.')

        self._detect_edit_global_transformation()

        for processor in self._fitting_sequence:
            if type(processor) == str:
                for col, obj in self._config[processor].items():
                    if obj is None:
                        continue
                    
                    obj.fit(data[col])
            else:
                # if the processor is not a string,
                # it should be a mediator, which could be fitted directly.
                processor.fit(data)
        

        self._is_fitted = True

    def _check_sequence_valid(self, sequence):
        if type(sequence) != list:
            raise TypeError('Sequence should be a list.')
        
        if len(sequence) == 0:
            raise ValueError('There should be at least one procedure in the sequence.')
        
        if len(sequence) > 4:
            raise ValueError('Too many procedures!')
        
        if len(list(set(sequence))) != len(sequence):
            raise ValueError('There are duplicated procedures in the sequence, please remove them.')
        
        for processor in sequence:
            if processor not in ['missingist', 'outlierist', 'encoder', 'scaler']:
                raise ValueError(f'{processor} is invalid, please check it again.')
            
    def _detect_edit_global_transformation(self):
        """
        Detect whether a processor in the config conducts global transformation.
        If it does, suppress other processors in the config.
        Only works with Outlierist currently.
        """
        is_global_transformation = False
        replaced_class = None

        for obj in self._config['outlierist'].values():
            if obj is None:
                continue
            if obj.IS_GLOBAL_TRANSFORMATION:
                is_global_transformation = True
                replaced_class = obj.__class__
                print(f'Global transformation detected. All processors will be replaced to {replaced_class}.')
                break

        if is_global_transformation:
            for col, obj in self._config['outlierist'].items():
                self._config['outlierist'][col] = replaced_class()

    
    def transform(self):
        if not self._is_fitted:
            raise UnfittedError('The object is not fitted. Use .fit() first.')

    def inverse_transform(self):
        if not self._is_fitted:
            raise UnfittedError('The object is not fitted. Use .fit() first.')

    def get_processor(self):
        pass

    
    # determine whether the processors are not default settings
    def get_changes(self):
        pass

