import asyncio
import json
from db import (
    insert_message, get_all_messages, get_private_messages, is_user_banned, 
    is_user_temporarily_kicked, get_user_last_messages, delete_message,
    get_all_unread_counts, mark_messages_as_read, increment_unread_for_all_users
)

# Initialize module-level variable
user_last_messages = get_user_last_messages()

connected_clients = {}  # { websocket: username }

async def notify_user_list():
    from db import get_all_registered_users, get_private_messages
    
    # Get all registered users
    all_users = get_all_registered_users()
    online_users = list(connected_clients.values())
    
    # Send user list with unread counts to each connected user
    for client, current_username in connected_clients.items():
        try:
            # Get unread counts for this specific user
            unread_counts = get_all_unread_counts(current_username)
            
            users_info = []
            for user in all_users:
                username = user['username']
                # Skip current user from the list
                if username == current_username:
                    continue
                    
                is_online = username in online_users
                
                # Get last private message between current user and this user
                private_messages = get_private_messages(current_username, username)
                if private_messages:
                    # Get the last message content
                    last_msg = private_messages[-1]['content']
                    # Truncate long messages for display
                    last_message = last_msg[:50] + "..." if len(last_msg) > 50 else last_msg
                else:
                    last_message = "No private messages yet"
                
                unread_count = unread_counts.get(username, 0)
                
                users_info.append({
                    "username": username,
                    "name": user['name'] or username,
                    "online": is_online,
                    "last_message": last_message,
                    "unread_count": unread_count
                })
            
            # Also add public chat unread count
            public_unread_count = unread_counts.get("PUBLIC", 0)
            
            message = json.dumps({
                "type": "user_list",
                "users": users_info,
                "public_unread_count": public_unread_count
            })
            
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
                        message_id = insert_message(
                            data["sender"], 
                            data["type"], 
                            data.get("content", ""), 
                            data.get("fileName", ""),
                            recipient=recipient,
                            is_private=True
                        )
                        
                        # Add message ID to the data
                        message_data = json.loads(message)
                        message_data["id"] = message_id
                        updated_message = json.dumps(message_data)
                        
                        # Update last messages cache for private messages
                        user_last_messages[data["sender"]] = data.get("content", "")
                        
                        # Send to recipient and sender only
                        target_clients = []
                        for client, username in connected_clients.items():
                            if username == recipient or username == data["sender"]:
                                target_clients.append(client)
                        
                        for client in target_clients:
                            await client.send(updated_message)
                        
                        # Increment unread count for the recipient (not the sender)
                        increment_unread_for_all_users(data["sender"], recipient, message_id)
                        
                        # Update user list with new last message and unread counts
                        await notify_user_list()
                    
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
                        
                elif data.get("message_type") == "delete_message":
                    # Handle message deletion
                    message_id = data.get("message_id")
                    if message_id:
                        result = delete_message(message_id, data["sender"])
                        if result["status"] == "success":
                            # Notify all clients that a message was deleted
                            for client in connected_clients:
                                await client.send(json.dumps({
                                    "type": "message_deleted",
                                    "message_id": message_id
                                }))
                
                elif data.get("message_type") == "mark_as_read":
                    # Handle marking messages as read
                    chat_partner = data.get("chat_partner")
                    if chat_partner:
                        mark_messages_as_read(data["sender"], chat_partner)
                        # Update user list to reflect new unread counts
                        await notify_user_list()
                        
                else:
                    # Public message handling (default)
                    message_id = insert_message(data["sender"], data["type"], data.get("content", ""), data.get("fileName", ""))
                    
                    # Add message ID to the data
                    message_data = json.loads(message)
                    message_data["id"] = message_id
                    updated_message = json.dumps(message_data)
                    
                    # Update last messages cache
                    user_last_messages[data["sender"]] = data.get("content", "")
                    
                    # Broadcast to all users
                    for client in connected_clients:
                        await client.send(updated_message)
                    
                    # Increment unread count for all users (except sender) for public messages
                    increment_unread_for_all_users(data["sender"], "PUBLIC", message_id)
                    
                    # Update user list with new last message and unread counts
                    await notify_user_list()

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
