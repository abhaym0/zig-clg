import asyncio
import json
from db import insert_message, get_all_messages

connected_clients = set()

async def handle_ws(connection):
    connected_clients.add(connection)
    try:
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
