"""
Admin APIs Module
"""

from .stats import app as stats_app
from .tasks import app as tasks_app
from .history import app as history_app
from .in_progress import app as in_progress_app
from .detail import app as detail_app
from .logs import app as logs_app

__all__ = [
    'stats_app',
    'tasks_app',
    'history_app',
    'in_progress_app',
    'detail_app',
    'logs_app',
]