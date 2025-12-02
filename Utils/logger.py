import os

def get_logger_config(log_level: str = "INFO") -> dict:
    os.makedirs("logs", exist_ok=True)
    level = log_level.upper() if log_level.upper() in ("DEBUG", "INFO", "WARNING") else "INFO"
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "clean": {
                "format": "%(asctime)s │ %(message)s",
                "datefmt": "%H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "clean",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/bot.log",
                "maxBytes": 5242880,
                "backupCount": 3
            }
        },
        "loggers": {
            "StarVell": {"level": level, "handlers": ["console", "file"], "propagate": False},
            "Nexus": {"level": level, "handlers": ["console", "file"], "propagate": False},
            "StarVellAPI": {"level": level, "handlers": ["console", "file"], "propagate": False},
            "aiogram": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "aiohttp": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": "WARNING", "handlers": ["console"]}
    }

LOGGER_CONFIG = get_logger_config("INFO")
