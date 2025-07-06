import asyncio
import json
from db import insert_message, get_all_messages

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

                # Insert into DB (you can later skip for private messages)
                insert_message(data["sender"], data["type"], data.get("content", ""), data.get("fileName", ""))

                # Broadcast message to all users (for now, still public)
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
