"""
Pytest configuration.
Suppresses third-party library warnings that we cannot fix.
"""

import warnings

# Suppress deprecation warnings from third-party packages
warnings.filterwarnings(
    'ignore',
    message='.*get_event_loop.*',
    category=DeprecationWarning,
    module='eventkit.*'
)

warnings.filterwarnings(
    'ignore',
    message='.*get_event_loop.*',
    category=DeprecationWarning,
    module='ib_insync.*'
)

