import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

# Define a WebSocket consumer class for handling asynchronous connections
class AnalysisConsumer(AsyncWebsocketConsumer):
    
    # Function that runs when a WebSocket connection is initiated
    async def connect(self):
        # If the user is anonymous, close the connection
        if self.scope["user"] == AnonymousUser():
            await self.close()
        else:
            # Add the user to the analysis group and notifications group if authenticated
            await self.channel_layer.group_add("analysis_group", self.channel_name)
            await self.channel_layer.group_add("notifications", self.channel_name)
            await self.accept()  # Accept the connection

    # Function that runs when the WebSocket connection is closed
    async def disconnect(self, close_code):
        # Remove the user from the analysis and notifications groups upon disconnection
        await self.channel_layer.group_discard("analysis_group", self.channel_name)
        await self.channel_layer.group_discard("notifications", self.channel_name)

    # Function to handle messages received from the WebSocket
    async def receive(self, text_data):
        try:
            # Parse the incoming text data into a JSON object
            text_data_json = json.loads(text_data)
            message = text_data_json['message']  # Extract the message from JSON
            # Get the type of message; default is 'general' if not specified
            message_type = text_data_json.get('type', 'general')

            # If the message type is 'analysis', send the message to the analysis group
            if message_type == 'analysis':
                await self.channel_layer.group_send(
                    "analysis_group",
                    {
                        'type': 'analysis_message',
                        'message': message
                    }
                )
            # If the message type is 'notification', send the message to the notifications group
            elif message_type == 'notification':
                await self.channel_layer.group_send(
                    "notifications",
                    {
                        'type': 'send_notification',
                        'message': message
                    }
                )
            # If the message type is neither, send it to both groups
            else:
                await self.channel_layer.group_send(
                    "analysis_group",
                    {
                        'type': 'analysis_message',
                        'message': message
                    }
                )
                await self.channel_layer.group_send(
                    "notifications",
                    {
                        'type': 'send_notification',
                        'message': message
                    }
                )

        # Handle cases where the incoming data is not valid JSON
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON format'}))
        # Handle cases where a required key is missing in the JSON data
        except KeyError:
            await self.send(text_data=json.dumps({'error': 'Missing key in JSON data'}))
        # Handle any other exceptions
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))

    # Function to send analysis messages to the WebSocket
    async def analysis_message(self, event):
        try:
            # Retrieve the message from the event and send it back to the WebSocket
            message = event['message']
            await self.send(text_data=json.dumps({
                'message': message
            }))
        # Handle invalid JSON errors
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON format'}))
        # Handle any other exceptions
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))

    # Function to send notification messages to the WebSocket
    async def send_notification(self, event):
        try:
            # Retrieve the message from the event and send it back to the WebSocket
            message = event['message']
            await self.send(text_data=json.dumps({
                'message': message
            }))
        # Handle invalid JSON errors
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON format'}))
        # Handle any other exceptions
        except Exception as e:
            await self.send(text_data=json.dumps({'error': str(e)}))
