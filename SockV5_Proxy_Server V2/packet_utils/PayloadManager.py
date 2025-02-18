import asyncio,zlib,struct

class PayloadManager:


    CONNS : dict[int,list[bool,asyncio.StreamReader,asyncio.StreamWriter]] = {}
    CONNS_LOCK = asyncio.Lock()

    def generate_packet(self,session_id, payload,msg_type):
        magic = 0xDEADBEEF  # Fixed magic value
        payload_length = len(payload)
        crc32 = zlib.crc32(payload) & 0xFFFFFFFF  # Compute CRC32 checksum
        
        header = struct.pack('=L H L H L', magic, session_id, crc32, msg_type, payload_length)
        return header + payload


    def __init__(self):
        self.conns  = self.CONNS
    
    @classmethod
    def GetConnListAndLock(cls):
        return (cls.CONNS,cls.CONNS_LOCK)
        

    async def Parse(self,**data):

        async with self.CONNS_LOCK:
            if data['type'] == 1: # Connect to target
                if data['chID'] in self.conns:
                    sw : asyncio.StreamWriter = self.conns[data['chID']][2]
                    if self.conns[data['chID']][0] == False:
                        self.conns[data['chID']][0] = True
                        try:    #Nasty Place made me waste lot of time.Problem was. Connection Lost Exception
                            sw.write(b'\x05\x00\x00\x01'+data['data'])
                            await sw.drain()
                        except:
                            pass


            

            elif data['type'] == 2:
                if data['chID'] in self.conns:
                    try:
                    
                        self.conns[data['chID']][2].write(data['data'])
                        await self.conns[data['chID']][2].drain()
                    except:
                        pass

            elif data['type'] == 0:
                
                if data['chID'] in self.conns and self.conns[data['chID']][0] == True:
                    self.conns[data['chID']][1].set_exception(Exception('Client Disconnect'))
                    del self.conns[data['chID']]
                
                elif data['chID'] in self.conns and self.conns[data['chID']][0] == False:
                    try:
                        self.conns[data['chID']][2].write(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                        await self.conns[data['chID']][2].drain()
                    except:
                        pass
                    self.conns[data['chID']][1].set_exception(Exception('Client Disconnect'))
                    del self.conns[data['chID']]

   