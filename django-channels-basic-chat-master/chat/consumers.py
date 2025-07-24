import json
import os
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from datetime import datetime

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'chat_room'

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

        # Send existing messages to client on connect
        messages = self.load_messages()
        for msg in messages:
            self.send(text_data=json.dumps({
                'type': 'chat',
                'message': msg['message'],
                'id': msg['id']
            }))

    def receive(self, text_data):
        data = json.loads(text_data)
        msg_id = data.get("id")
        message_type = data.get("type", "chat")
        message_file = os.path.join(os.path.dirname(__file__), 'messages.json')

        if message_type == "delete":
            # Remove from JSON
            messages = self.load_messages()
            messages = [msg for msg in messages if msg['id'] != msg_id]
            self.save_messages(messages)

            # Broadcast delete
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'delete_message',
                    'id': msg_id
                }
            )
            return

        # Save new message
        new_msg = {
            'id': msg_id,
            'message': data['message'],
            'timestamp': datetime.now().isoformat()
        }

        messages = self.load_messages()
        messages.append(new_msg)
        self.save_messages(messages)

        # Broadcast new message
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': new_msg['message'],
                'id': new_msg['id']
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'id': event['id']
        }))

    def delete_message(self, event):
        self.send(text_data=json.dumps({
            'type': 'delete',
            'id': event['id']
        }))

    def load_messages(self):
        path = os.path.join(os.path.dirname(__file__), 'messages.json')
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_messages(self, messages):
        path = os.path.join(os.path.dirname(__file__), 'messages.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2)
