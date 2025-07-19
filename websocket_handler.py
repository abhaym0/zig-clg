import asyncio
import json
from db import insert_message, get_all_messages, get_private_messages, is_user_banned, is_user_temporarily_kicked

connected_clients = {}  # { websocket: username }

async def notify_user_list():
    users = list(connected_clients.values())
    message = json.dumps({
        "type": "user_list",
        "users": users
    })
    for client in connected_clients:
        try:
            await client.send(message)
        except:
            pass  # you may log this

async def handle_ws(connection):
    try:
        # Wait for client to send their username first
        initial = await connection.recv()
        data = json.loads(initial)
        username = data.get("username")

        if not username:
            await connection.send(json.dumps({"type": "error", "message": "Username required"}))
            return
        
        # Check if user is banned
        if is_user_banned(username):
            await connection.close(code=1008, reason="You have been banned")
            return
        
        # Check if user is temporarily kicked
        kick_status = is_user_temporarily_kicked(username)
        if kick_status["is_kicked"]:
            import datetime
            kick_until = datetime.datetime.fromisoformat(kick_status["kick_until"])
            remaining_time = kick_until - datetime.datetime.now()
            minutes_remaining = int(remaining_time.total_seconds() / 60)
            
            kick_message = f"You are temporarily restricted from joining the chat. {minutes_remaining} minutes remaining. Reason: {kick_status['reason']}"
            await connection.close(code=1008, reason=kick_message)
            return

        connected_clients[connection] = username
        print(f"[INFO] {username} connected.")

        # Send previous messages to this user
        previous_messages = get_all_messages()
        for msg in previous_messages:
            await connection.send(json.dumps(msg))

        # Notify all users of new connection
        await notify_user_list()

        # Listen for messages
        async for message in connection:
            print(f"[LOG] Message: {message}")
            try:
                data = json.loads(message)
                
                # Handle different message types
                if data.get("message_type") == "private":
                    # Private message handling
                    recipient = data.get("recipient")
                    if recipient:
                        # Save to database as private message
                        insert_message(
                            data["sender"], 
                            data["type"], 
                            data.get("content", ""), 
                            data.get("fileName", ""),
                            recipient=recipient,
                            is_private=True
                        )
                        
                        # Send to recipient and sender only
                        target_clients = []
                        for client, username in connected_clients.items():
                            if username == recipient or username == data["sender"]:
                                target_clients.append(client)
                        
                        for client in target_clients:
                            await client.send(message)
                    
                elif data.get("message_type") == "get_private_messages":
                    # Send private message history
                    other_user = data.get("other_user")
                    if other_user:
                        private_messages = get_private_messages(data["sender"], other_user)
                        response = {
                            "type": "private_message_history",
                            "other_user": other_user,
                            "messages": private_messages
                        }
                        await connection.send(json.dumps(response))
                        
                else:
                    # Public message handling (default)
                    insert_message(data["sender"], data["type"], data.get("content", ""), data.get("fileName", ""))
                    
                    # Broadcast to all users
                    for client in connected_clients:
                        await client.send(message)

            except Exception as e:
                print("Error handling message:", e)

    except Exception as e:
        print("WebSocket error:", e)

    finally:
        # Remove disconnected user
        if connection in connected_clients:
            disconnected_user = connected_clients.pop(connection)
            print(f"[INFO] {disconnected_user} disconnected.")
            await notify_user_list()
