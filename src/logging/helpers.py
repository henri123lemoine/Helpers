import logging
from functools import wraps
from inspect import signature

logger = logging.getLogger("logging")


def format_args(method, args, kwargs):
    sig = signature(method)
    bound_args = sig.bind_partial(*args, **kwargs)
    bound_args.apply_defaults()
    formatted_args = []
    for name, value in bound_args.arguments.items():
        if name == "self":  # Skip 'self' parameter
            continue
        if isinstance(value, str):
            formatted_args.append(f"{name}='{value}'")
        else:
            formatted_args.append(f"{name}={value}")
    return ", ".join(formatted_args)


def log_method_call(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        formatted_args = format_args(method, args, kwargs)
        if method.__name__ == "run_app":
            logger.info(f"From {self.__class__.__name__}, running run_app(debug={args[0]})")
        else:
            logger.info(
                f"From {self.__class__.__name__}, running {method.__name__}().{args[0]}({formatted_args})"
            )
        return method(self, *args, **kwargs)

    return wrapper


def log_all_methods(cls):
    for attr_name, attr_value in cls.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            setattr(cls, attr_name, log_method_call(attr_value))
    return cls
