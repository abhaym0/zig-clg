import asyncio

connected_clients = set()

async def handle_ws(connection):
    connected_clients.add(connection)
    try:
        async for message in connection:
            print(f"[LOG] Message: {message}")
            stale = set()
            for client in connected_clients:
                try:
                    await client.send(message)
                except:
                    stale.add(client)
            connected_clients.difference_update(stale)
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        connected_clients.discard(connection)