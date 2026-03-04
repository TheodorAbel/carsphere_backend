import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AvailabilityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("availability", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("availability", self.channel_name)

    async def availability_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            self.group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def user_notification(self, event):
        await self.send(text_data=json.dumps(event))
