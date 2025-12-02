import logging
from StarVellAPI.updater import events

logger = logging.getLogger("StarVellBot.plugins.test")

class Plugin:
    
    def __init__(self, context):
        self.nexus = context.get("nexus")
        
        self.name = "TestPlugin"
        self.version = "1.0.0"
        self.author = "@AnastasiaPisun"
        self.description = "Тест"
        self.enabled = True
        
        self.commands = [
            {"command": "test", "description": "Тест"},
        ]
        
        self.buttons = []
        
        logger.info(f"Плагин {self.name} инициализирован")
    
    def on_new_order(self, event: events.NewOrderEvent):
        if not self.enabled:
            return
        order = event.order
        logger.info(f"[{self.name}] Новый заказ: #{order.id} - {order.description}")
    
    def on_order_status_changed(self, event: events.OrderStatusChangedEvent):
        if not self.enabled:
            return
        order = event.order
        logger.info(f"[{self.name}] Статус заказа #{order.id} изменен на {order.status}")
    
    def on_new_message(self, event: events.NewMessageEvent):
        if not self.enabled:
            return
        message = event.message
        logger.info(f"[{self.name}] Новое сообщение от {message.author}: {message.text}")
    
    def on_chats_changed(self, event: events.ChatsListChangedEvent):
        if not self.enabled:
            return
        logger.info(f"[{self.name}] Список чатов изменился")
    
    def stop(self):
        logger.info(f"Плагин {self.name} остановлен")
