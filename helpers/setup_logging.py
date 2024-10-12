import logging
from logging.handlers import RotatingFileHandler

def setup_logging(name):
    """
    Set up a logger with console and file handlers.

    Objective:
    - Create a logger that outputs colored logs to the console and plain logs to a file.

    Input:
    - name (str): The name of the logger, used for both the logger instance and the log file.

    Output:
    - logger (logging.Logger): A configured logger instance.
    - function saves logs to "logs/" + name + ".log"

    How it works:
    1. Define a CustomFormatter class for colored console output.
    2. Create a logger instance with the given name.
    3. Set up a console handler with colored output for all log levels.
    4. Set up a rotating file handler for logs of INFO level and above.
    5. Configure formatters for both handlers.
    6. Add both handlers to the logger.
    7. Return the configured logger.
    """

    # ANSI escape sequences for coloring text in the console
    class CustomFormatter(logging.Formatter):
        """Custom formatter to add colors based on log level."""
        
        # Define color codes for different log levels
        COLORS = {
            'DEBUG': '\033[92m',  # Green
            'INFO': '\033[94m',   # Blue
            'WARNING': '\033[93m',# Yellow
            'ERROR': '\033[91m',  # Red
            'CRITICAL': '\033[95m'# Magenta
        }
        RESET = '\033[0m'  # Reset color

        def format(self, record):
            # Get the original format
            log_msg = super().format(record)
        
            # Apply color based on the log level
            color = self.COLORS.get(record.levelname, self.RESET)
            return f"{color}{log_msg}{self.RESET}"


    # Create logger
    logger = logging.getLogger(name)

    # Set logger level
    logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a rotating file handler (output logs to a file with size limit)
    # Set maxBytes to limit file size (e.g., 1MB = 1,000,000 bytes), and backupCount for how many backup files to keep
    file_handler = RotatingFileHandler('logs/' + name + '.log', maxBytes=10000000, backupCount=5)
    file_handler.setLevel(logging.INFO)

    # Create a formatter for file logs (no color)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Apply color to console logs using the custom formatter
    console_formatter = CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a formatter (specify the format for log messages)
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

