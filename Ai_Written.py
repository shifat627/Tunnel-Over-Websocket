# --------------------------
# server.py (HTTP Middleman)
# --------------------------
import asyncio
import websockets

class Server:
    def __init__(self):
        self.agent_conn = None
        self.client_conns = set()

    async def handler(self, websocket, path):
        if path == '/agent':
            await self.handle_agent(websocket)
        elif path == '/client':
            await self.handle_client(websocket)
        else:
            await websocket.close()

    async def handle_agent(self, websocket):
        self.agent_conn = websocket
        try:
            async for message in websocket:
                for client in self.client_conns:
                    await client.send(message)
        finally:
            self.agent_conn = None

    async def handle_client(self, websocket):
        self.client_conns.add(websocket)
        try:
            async for message in websocket:
                if self.agent_conn:
                    await self.agent_conn.send(message)
        finally:
            self.client_conns.remove(websocket)

async def main():
    server = Server()
    start_server = websockets.serve(server.handler, "0.0.0.0", 8765)
    await start_server
    await asyncio.Future()  # Run forever

asyncio.run(main())

# --------------------------
# agent.py (Target Agent)
# --------------------------
import asyncio
import websockets
import json

class Agent:
    def __init__(self):
        self.connections = {}

    async def connect_target(self, conn_id, host, port):
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self.connections[conn_id] = (reader, writer)
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    async def handle_messages(self, websocket):
        async for message in websocket:
            if isinstance(message, bytes):
                await self.handle_data(message)
            else:
                await self.handle_control(message, websocket)

    async def handle_control(self, message, websocket):
        try:
            msg = json.loads(message)
            if msg['type'] == 'connect':
                conn_id = msg['conn_id']
                success = await self.connect_target(conn_id, msg['host'], msg['port'])
                response = {'type': 'status', 'conn_id': conn_id, 
                           'status': 'success' if success else 'fail'}
                await websocket.send(json.dumps(response))
        except json.JSONDecodeError:
            pass

    async def handle_data(self, message):
        conn_id = message[:16].decode().strip('\x00')
        data = message[16:]
        if conn_id in self.connections:
            writer = self.connections[conn_id][1]
            writer.write(data)
            await writer.drain()

    async def run(self):
        uri = "ws://localhost:8765/agent"
        async with websockets.connect(uri) as websocket:
            await self.handle_messages(websocket)

if __name__ == "__main__":
    agent = Agent()
    asyncio.run(agent.run())

# --------------------------
# socks5.py (SOCKS5 Server)
# --------------------------
import asyncio
import websockets
import json
import struct

class SocksProxy:
    def __init__(self):
        self.connections = {}

    async def handle_client(self, reader, writer):
        # SOCKS5 Handshake
        await reader.read(2)  # Version and method count
        writer.write(b'\x05\x00')  # No auth required
        await writer.drain()

        # Request handling
        version, cmd, _, addr_type = await reader.read(4)
        if version != 5 or cmd != 1:
            writer.close()
            return

        if addr_type == 1:  # IPv4
            addr = await reader.read(4)
            addr = '.'.join(map(str, addr))
        elif addr_type == 3:  # Domain name
            domain_len = await reader.read(1)
            addr = await reader.read(ord(domain_len))
            addr = addr.decode()
        else:
            writer.close()
            return

        port = await reader.read(2)
        port = struct.unpack('!H', port)[0]

        # Create WebSocket connection
        conn_id = struct.pack('!Q', id(writer)).rjust(16, b'\x00')
        self.connections[id(writer)] = conn_id
        
        async with websockets.connect("ws://localhost:8765/client") as ws:
            # Send connection request
            await ws.send(json.dumps({
                'type': 'connect',
                'conn_id': conn_id.decode(),
                'host': addr,
                'port': port
            }))

            # Wait for response
            response = await ws.recv()
            status = json.loads(response).get('status', 'fail')
            
            if status == 'success':
                writer.write(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
                await writer.drain()
                
                # Start data forwarding
                await asyncio.gather(
                    self.forward_local_to_remote(reader, ws, conn_id),
                    self.forward_remote_to_local(writer, ws)
                )
            else:
                writer.write(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                await writer.drain()

        writer.close()

    async def forward_local_to_remote(self, reader, ws, conn_id):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                await ws.send(conn_id + data)
        except:
            pass

    async def forward_remote_to_local(self, writer, ws):
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    writer.write(message[16:])  # Strip connection ID
                    await writer.drain()
        except:
            pass

async def main():
    server = await asyncio.start_server(
        lambda r, w: SocksProxy().handle_client(r, w), 
        '0.0.0.0', 1080
    )
    async with server:
        await server.serve_forever()

asyncio.run(main())