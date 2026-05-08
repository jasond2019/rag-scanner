"""
Report APIs Module
"""

from .generate import app as generate_app
from .download import app as download_app

__all__ = [
    'generate_app',
    'download_app',
]