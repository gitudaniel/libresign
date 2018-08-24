
import functools
import inspect

def type_check(wrapped):
    ''' Type check arguments and return type based on
        function type decorations.

        Source:
            https://stackoverflow.com/a/17495541
    '''

    def replace(obj, old, new):
        return new if obj is old else obj

    signature = inspect.signature(wrapped)
    parameter_values = signature.parameters.values()
    parameter_names = tuple(parameter.name for parameter in parameter_values)
    parameter_types = tuple(
        replace(parameter.annotation, parameter.empty, object)
        for parameter in parameter_values
    )
    return_type = replace(signature.return_annotation, signature.empty, object)

    @functools.wraps(wrapped)
    def wrapper(*arguments, **kwargs):
        for argument, parameter_type, parameter_name in zip(
            arguments, parameter_types, parameter_names
        ):
            if not isinstance(argument, parameter_type):
                raise TypeError(f'{parameter_name} should be of type '
                                f'{parameter_type.__name__}, not '
                                f'{type(argument).__name__}')
        result = wrapped(*arguments, **kwargs)
        if not isinstance(result, return_type):
            raise TypeError(f'return should be of type '
                            f'{return_type.__name__}, not '
                            f'{type(result).__name__}')
        return result
    return wrapper
