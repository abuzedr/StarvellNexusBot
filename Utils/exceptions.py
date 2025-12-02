class StarVellBotException(Exception):
    pass

class ConfigParseError(StarVellBotException):
    pass

class PluginLoadError(StarVellBotException):
    pass

class TelegramBotError(StarVellBotException):
    pass

class DatabaseError(StarVellBotException):
    pass
