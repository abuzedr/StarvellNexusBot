# tg_bot/__init__.py
"""
Telegram bot модуль для StarVellBot (aiogram 3.x)
"""

from .aio_bot import AioTGBot
from .CBT import *

__all__ = ["AioTGBot"]