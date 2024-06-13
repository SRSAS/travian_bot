import concurrent.futures
import time
from functools import wraps, partial
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

executor = concurrent.futures.ThreadPoolExecutor()


def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        current_time = datetime.now().strftime('%H:%M:%S')
        logger.info(f'Function {func.__name__} started execution at {current_time}.')

        result = func(*args, **kwargs)

        current_time = datetime.now().strftime('%H:%M:%S')
        logger.info(f'Function {func.__name__} finished execution at {current_time}.')

        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f'Total execution time: {execution_time:4f} seconds')
        return result

    return wrapper


def retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.info(f'Function {func.__name__} failed, with error {e}. Retrying...')

    return wrapper


def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        future = executor.submit(func, *args, **kwargs)
        return future

    return wrapper


def as_command(func, log=False, threaded=False, **kwargs):
    if threaded:
        if log:
            return run_async(log_execution_time(partial(func, **kwargs)))
        return run_async(partial(func, **kwargs))

    if log:
        return log_execution_time(partial(func, **kwargs))

    return partial(func, **kwargs)


class Option:
    def __init__(self, name="", command=None):
        self.name = name or ""
        self.command = command or partial(print, "No command provided")

    def __str__(self):
        return self.name

    def __call__(self):
        self.command()


class Menu:
    def __init__(self, options=None, title=""):
        option_list = options or []
        self.options = {}
        for option in option_list:
            self.options[option.name] = option
        self.title = title or ""

    def __str__(self):
        return self.title

    def __call__(self, *args, **kwargs):
        while True:
            self.display()
            option = input()
            if option.isdigit():
                option_num = int(option)

                if 0 < option_num <= len(self.options):
                    option = list(self.options.keys())[option_num - 1]
                    self.options[option]()
                elif option_num == 0:
                    return
                else:
                    self.display_usage()
            else:
                if option == 'quit':
                    return
                elif option in self.options.keys():
                    self.options[option]()
                else:
                    self.display_usage()

    def add_option(self, option_name, option_command):
        self.options[option_name] = option_command

    def remove_option(self, option_name):
        self.options.pop(option_name)

    def display_usage(self):
        print("Invalid option.")
        print("Please select an option name or number:")
        self.display_options()

    def display(self):
        print(self.title)
        self.display_options()

    def display_options(self):
        option_index = 1
        for option in self.options.keys():
            print(f'{option_index} - {str(option)}')
            option_index += 1
        print(f'{option_index} - quit')
