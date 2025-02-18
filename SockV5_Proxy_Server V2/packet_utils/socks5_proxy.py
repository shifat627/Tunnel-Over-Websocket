import socket,aiohttp,zlib,random,asyncio,struct,traceback,os


class SockV5Handler:
    '''
    This Class Will used with client handler of asyncio.start_server.
    You Need to pass:
    - ws connection to ws server
    - a dictonary that is used by both Header handler and client handler
    - A Lock
    - stream reader , writer of cient

    '''
    remote_ws = None
    conns = None
    _session_counter = 0
    conns_lock = None
    Lock = asyncio.Lock() #Ws Lock

    @classmethod
    def SetParam(cls,ws : aiohttp.ClientWebSocketResponse, conn_info : dict,Lock):
        cls.remote_ws : aiohttp.ClientWebSocketResponse = ws
        cls.conns = conn_info
        cls.conns_lock = Lock

    def generate_packet(self,session_id, payload,msg_type):
        magic = 0xDEADBEEF  # Fixed magic value
        payload_length = len(payload)
        crc32 = zlib.crc32(payload) & 0xFFFFFFFF  # Compute CRC32 checksum
        
        header = struct.pack('=L H L H L', magic, session_id, crc32, msg_type, payload_length)
        return header + payload
    
    async def generate_unique_session_id(self):
        
        async with self.conns_lock:
            while True:
                r = random.randint(0,0xffff)
                if r not in self.conns:
                    self.session_id = r
                    break
        
        

        
    def __init__(self,  verbose : bool , c_sr : asyncio.StreamReader , c_sw: asyncio.StreamWriter):
        #self.conns : dict[int,list[bool,asyncio.StreamReader,asyncio.StreamWriter]] = conn_info
        #self.remote_ws = ws
        self.client_sr = c_sr
        self.client_sw = c_sw
        
        self.verbose = verbose
        self.session_id = 0
        
        self.remote_host = {}
        

    async def Authentication_Stage(self,AUTH_TYPE):
        readS = self.client_sr
        writeS = self.client_sw
        
        methods = []


        if self.verbose:
            print('Authentication Stage.......')

        try:
            version , nmethods = struct.unpack('=BB',await readS.readexactly(2))
            
            if version != 5:
                if self.verbose:
                    print('Invalid Verison Detected')
                return False
            
            if nmethods == 0:
                if self.verbose:
                    print('No Auth is Identified')
                return False
            
            methods.extend(struct.unpack('='+'B'*nmethods,await readS.readexactly(nmethods)))

            if self.verbose:
                print(f'Verison : {version}\nTotal Methods: {nmethods}')
                print('Methods: ',methods)

            if AUTH_TYPE not in methods:
                if self.verbose:
                    print('Prefered Auth is not Found')
                
                writeS.write(b'\x05\xff')
                await writeS.drain()

                return False

            if AUTH_TYPE == 0:
                writeS.write(b'\x05\x00')
                await writeS.drain()
            if AUTH_TYPE == 2:
                pass
            


        except Exception as Err:
            if self.verbose:
                print(str(Err))
            return False
        
        return True


    async def Resolve_Remote_Host_IpPort(self,Type : int):
        ip = ''
        dns_name = ''
        port = 0
        reader = self.client_sr
        ip_six = ''
        
        if Type == 1:
            #ip = int.from_bytes(await reader.readexactly(4),'big')
            ip = socket.inet_ntoa(await reader.readexactly(4))
        elif Type == 3:
            dns_name_len = int.from_bytes(await reader.readexactly(1))
            dns_name = (await reader.readexactly(dns_name_len)).decode()
        elif Type == 4:
            ip_six = socket.inet_ntop(socket.AF_INET6,await reader.readexactly(16))
        else:
            return False
        
        port = int.from_bytes(await reader.readexactly(2),'big')
        
        if Type == 1:
            self.remote_host['ip'] = ip
            self.remote_host['port'] = port
            self.remote_host['dns_name'] = ''
            self.remote_host['type'] = Type
            return (ip,port)
        if Type == 3:
            
            self.remote_host['port'] = port
            self.remote_host['ip'] = dns_name
            self.remote_host['type'] = Type
        if Type == 4:
            print(ip_six)
            self.client_sw.write(b'\x05\x08\x00'+Type.to_bytes(1)+socket.inet_pton(socket.AF_INET6,ip_six)+port.to_bytes(2,'big'))
            await self.client_sw.drain()
            return False


        return True

    
    async def Resolve_Remote_Host(self):
        readS = self.client_sr
        writeS = self.client_sw
        try:
            version , cmd , _ , address_type = struct.unpack('=BBBB',await readS.readexactly(4))
            
            if version != 5:
                if self.verbose:
                    print('Invalid Verison Detected')
                return False
            

            if self.verbose:
                print(f'Command: {cmd}\tAddress Type: {address_type}')

            if cmd == 1:
                if not await self.Resolve_Remote_Host_IpPort(address_type):
                    return False

                if self.verbose:
                    print(self.remote_host)

                
                
            else:
                return False


            
        except Exception as Err:
            if self.verbose:
                print(traceback.print_exc())
            return False
        
        return True    
    


    async def HandShake(self,AUTH_METHOD):
        await self.generate_unique_session_id()

        if ( (await self.Authentication_Stage(AUTH_METHOD)) != True ):
            return False

        if ( (await self.Resolve_Remote_Host()) != True ):
            return False

        if ( (await self.SendConnectHeader()) != True ):
            return False

        await asyncio.gather(self.ClientTORemote())

        return True
    

    async def SendConnectHeader(self):
        try:
            ConnPayload = b''
            ConnType = 1
            if self.remote_host['type'] == 1:
                ConnType = 1
                ConnPayload += socket.inet_aton(self.remote_host['ip']) + int.to_bytes(self.remote_host['port'],2,'big')
            elif self.remote_host['type'] == 3:
                ConnType = 4
                ConnPayload +=  int.to_bytes(self.remote_host['port'],2,'big') + int.to_bytes(len(self.remote_host['ip']),1,'little') + self.remote_host['ip'].encode()
            
            ConnHeader = self.generate_packet(self.session_id,ConnPayload,ConnType)
            
            async with self.Lock:
                if not self.remote_ws.closed:
                    await self.remote_ws.send_bytes(ConnHeader)
            
            async with self.conns_lock:
                self.conns[self.session_id] = [False,self.client_sr,self.client_sw] # To differentiate


            

            

        except Exception as Err:
            if self.verbose:
                print(traceback.print_exc())
            
            
            return False
        
        return True
    
    async def ClientTORemote(self):
        try:
            while True:
                data = await self.client_sr.read(1024)
                if not data:
                    
                    break

                Header = self.generate_packet(self.session_id,data,2)

                async with self.Lock:
                    if not self.remote_ws.closed:
                        await self.remote_ws.send_bytes(Header)
                


        except Exception as Err:
            if self.verbose:
                print(traceback.print_exc())

        finally:
            Header = self.generate_packet(self.session_id,b'',3)
            
            async with self.Lock:
                if not self.remote_ws.closed:
                    await self.remote_ws.send_bytes(Header)
            

            self.client_sw.close() # Throws Some Execption for COnnection LOst
            await self.client_sw.wait_closed() # Throws Some Execption for COnnection LOst
            
        if self.verbose:
            print('Exitining ClientTORemote')
