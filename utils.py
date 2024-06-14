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
    def __init__(self, options=None, title="", on_open=None, on_close=None):
        option_list = options or []
        self.options = {}
        for option in option_list:
            self.options[option.name] = option
        self.title = title or ""

        self.on_open = on_open or []
        self.on_close = on_close or []

        self.running = True

    def __str__(self):
        return self.title

    def __call__(self, *args, **kwargs):
        self.open()
        while self.running:
            self.process_user_input()

    def process_user_input(self):
        self.display()

        option = input()
        if option.isdigit():
            self.process_numeric_input(option)
        else:
            self.process_string_input(option)

    def process_numeric_input(self, user_input):
        option_num = int(user_input)

        if 0 < option_num <= len(self.options):
            option_keys = list(self.options.keys())
            user_input = option_keys[option_num - 1]
            self.options[user_input]()
        elif option_num == 0:
            self.close()
        else:
            Menu.display_invalid_option_warning()

    def process_string_input(self, user_input):
        if user_input in self.options.keys():
            self.options[user_input]()
        elif user_input == 'quit':
            self.close()
        else:
            Menu.display_invalid_option_warning()

    def add_option(self, option_name, option_command):
        self.options[option_name] = option_command

    def remove_option(self, option_name):
        self.options.pop(option_name)

    def add_on_open(self, command):
        self.on_open.append(command)

    def add_on_close(self, command):
        self.on_close.append(command)

    def open(self):
        self.running = True
        for command in self.on_open:
            command()

    def close(self):
        self.running = False
        for command in self.on_close:
            command()

    @staticmethod
    def display_invalid_option_warning():
        print("Invalid option.")
        print("Please select an option name or number:")

    def display(self):
        print(self.title)
        self.display_options()

    def display_options(self):
        option_index = 1
        for option in self.options.keys():
            print(f'{option_index} - {str(option)}')
            option_index += 1
        print(f'{option_index} - quit')
