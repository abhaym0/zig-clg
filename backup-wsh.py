import asyncio
import json
from db import insert_message, get_all_messages

connected_clients = set()
connected_users = {}

async def handle_ws(connection):
    connected_clients.add(connection)
    try:

        init_msg = await connection.recv()
        init_data = json.loads(init_msg)
        if init_data.get("type") != "join":
            await connection.send(json.dumps({"type": "error", "message": "First message must be of type 'join'"}))
            return
        
        username = init_data.get("sender", "Anonymous")

        connected_users[connection] = username

        join_msg = json.dumps({
            "type": "system",
            "sender": "System",
            "content": f"{username} joined the chat."
        })
        await broadcast(join_msg)

        # Optional: send chat history to the newly connected user
        previous_messages = get_all_messages()
        for msg in previous_messages:
            await connection.send(json.dumps(msg))

        async for message in connection:
            print(f"[LOG] Message: {message}")
            try:
                data = json.loads(message)
                # Insert into database
                insert_message(data["sender"], data["type"], data.get("content", ""), data.get("fileName", ""))

                # Broadcast to all clients
                stale = set()
                for client in connected_clients:
                    try:
                        await client.send(message)
                    except:
                        stale.add(client)
                connected_clients.difference_update(stale)

            except Exception as e:
                print("Error handling message:", e)

    except Exception as e:
        print("WebSocket error:", e)
    finally:
        connected_clients.discard(connection)
        left_username = connected_users.pop(connection, None)
        if left_username:
            leave_msg = json.dumps({
                "type": "system",
                "sender": "System",
                "content": f"{left_username} left the chat."
            })
            await broadcast(leave_msg)


async def broadcast(message):
    stale = []
    for client in connected_users:
        try:
            await client.send(message)
        except:
            stale.append(client)
    for client in stale:
        connected_users.pop(client, None)
