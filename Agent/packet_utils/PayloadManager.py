import asyncio,websockets,zlib,struct,socket,traceback

class PayloadManager:


    def generate_packet(self,session_id, payload,msg_type):
        magic = 0xDEADBEEF  # Fixed magic value
        payload_length = len(payload)
        crc32 = zlib.crc32(payload) & 0xFFFFFFFF  # Compute CRC32 checksum
        
        header = struct.pack('=L H L H L', magic, session_id, crc32, msg_type, payload_length)
        return header + payload


    def __init__(self,ws):
        self.semaphore = asyncio.locks.Lock()
        self.client_list : dict[int,tuple[asyncio.StreamReader,asyncio.StreamWriter]] = {}
        self.ws_client :websockets.WebSocketClientProtocol = ws
        self.TaskList : dict[int,asyncio.Task] = {}
        

    async def Parse(self,**data):

        if data['type'] == 1: # Connect to target
            ip = socket.inet_ntoa(data['data'][:4])
            port = int.from_bytes(data['data'][4:],'big')
            print(ip,port)
            conn = await self.ConnectToTarget(ip,port,data['chID'])
            if conn is not None:
                self.client_list[data['chID']] = conn
                self.TaskList[data['chID']] = asyncio.create_task(self.HandleClient(data['chID']))
            else:
                await self.SendDisconnectHeader(data['chID'])
        

        if data['type'] == 4: # Connect to target
            port = int.from_bytes(data['data'][:2],'big')
            host = data['data'][3:]
            
            ip = ''
            print(host,port)
            try:
                ip = socket.gethostbyname(host.decode())
            except:
                pass

            conn = await self.ConnectToTarget(ip,port,data['chID'])
            if conn is not None:
                self.client_list[data['chID']] = conn
                self.TaskList[data['chID']] = asyncio.create_task(self.HandleClient(data['chID']))
            else:
                await self.SendDisconnectHeader(data['chID'])
        

        elif data['type'] == 2:
            if data['chID'] in self.client_list:
                try:
                    self.client_list[data['chID']][1].write(data['data'])
                    await self.client_list[data['chID']][1].drain()
                except:
                    pass

        elif data['type'] == 3:
            if data['chID'] in self.TaskList:
                self.TaskList[data['chID']].cancel()
        
        elif data['type'] == 10:
            print('Closing all connection')
            for key in self.TaskList:
                self.TaskList[key].cancel()

    
    async def ConnectToTarget(self,target, port,chID):
        try:
            # sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP)
            # sock.connect((target,port))

            #header = int.to_bytes(0xdeadbeef,4,'little') + int.to_bytes(chID,2,'little') + int.to_bytes(0,4,'little') + int.to_bytes(0x0,2,'little') + int.to_bytes(0,4,'little')
            
            stream = await asyncio.open_connection(target,port)

            header = self.generate_packet(chID,socket.inet_aton(target) + int.to_bytes(port,2,'big'),1)
        
            async with self.semaphore:
                await self.ws_client.send(header)
            

            

            return stream
        
        except Exception as Err:
            traceback.print_exc()
            
        
        return None
        
    
    async def SendDisconnectHeader(self,chID):
        #header = int.to_bytes(0xdeadbeef,4,'little') + int.to_bytes(chID,2,'little') + int.to_bytes(0,4,'little') + int.to_bytes(0x1,2,'little') + int.to_bytes(0,4,'little')
        header = self.generate_packet(chID,b'',0)
        
        async with self.semaphore:
            await self.ws_client.send(header)
        

        
    async def HandleClient(self,chID):
        
        try:
            sr : asyncio.StreamReader = self.client_list[chID][0]
            
            while True:
                #data = await self.client_list[chID][0].read(1024)
                data = await sr.read(1024)
                if len(data) != 0:
                    async with self.semaphore:
                        await self.ws_client.send(self.generate_packet(chID,data,2))
                    
                else:
                    raise Exception('Disconnected')
        except:
            traceback.print_exc()
        finally:
             
            if chID in self.client_list:
                self.client_list[chID][1].close()
                await self.client_list[chID][1].wait_closed()
                del self.client_list[chID]
            if chID in self.TaskList:
                del self.TaskList[chID]
            
            await self.SendDisconnectHeader(chID)
            
 