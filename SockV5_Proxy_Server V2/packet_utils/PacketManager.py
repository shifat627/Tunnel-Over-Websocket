import struct,time,zlib

class PacketManager:


    # 4 bytes Magic bytes(0xdeadbeef) + 2 bytes channel ID + 4 bytes crc32 + 2 bytes type + 4 bytes payload length + payload 

    HEADER_LENGTH = 16

    def __init__(self):
        self.MODE = 0
        self.buffer = bytearray()
        self.CURENT_PAYLOAD_INFO = []
        self.PAYLOAD_LEN = 0


        

    def feed(self,data : bytes):
        self.buffer += data
    

    def _parse(self):
        
        if self.MODE == 0 and len(self.buffer) >= self.HEADER_LENGTH:

            Header = bytes(self.buffer[:self.HEADER_LENGTH])
            
            
            del self.buffer[:self.HEADER_LENGTH]

            
            self.CURENT_PAYLOAD_INFO.extend(struct.unpack("=LHLHL",Header))
            
            magic , chID , crc32_sum , payload_type , payload_size =  self.CURENT_PAYLOAD_INFO

            if magic == 0xdeadbeef:
                if payload_size == 0:
                    self.CURENT_PAYLOAD_INFO.clear()
                    return { 'type' : payload_type , 'chID' : chID , 'sum' : crc32_sum , 'size': payload_size , 'magic': magic}
                else:
                    self.MODE = 1
                    self.PAYLOAD_LEN = payload_size
                    self.CURENT_PAYLOAD_INFO.append(time.time())
            else:
                self.CURENT_PAYLOAD_INFO.clear()


        if self.MODE == 1:

            if (time.time() - self.CURENT_PAYLOAD_INFO[-1]) > 10.0 and len(self.buffer) < self.PAYLOAD_LEN:
                print('TimeOut Error')
                self.MODE = 0
                self.PAYLOAD_LEN = 0
                self.CURENT_PAYLOAD_INFO.clear()
                # self.buffer.clear()

                Index = self.buffer.find(int.to_bytes(0xdeadbeef,4,'little'))
                if Index == -1:
                    self.buffer.clear()
                else:
                    del self.buffer[:Index]



            
            elif len(self.buffer) >= self.PAYLOAD_LEN:
                magic , chID , crc32_sum , payload_type , payload_size , _ =  self.CURENT_PAYLOAD_INFO
                payload = bytes(self.buffer[:self.PAYLOAD_LEN])

                if (zlib.crc32(payload) & 0xffffffff ) != crc32_sum:
                    print('CheckSum Error')
                    Index = self.buffer.find(int.to_bytes(0xdeadbeef,4,'little'))
                    if Index == -1:
                        self.buffer.clear()
                    else:
                        del self.buffer[:Index]
                    
                    self.MODE = 0
                    self.PAYLOAD_LEN = 0
                    self.CURENT_PAYLOAD_INFO.clear()
                
                else:
                    del self.buffer[:self.PAYLOAD_LEN]
                    self.MODE = 0
                    self.PAYLOAD_LEN = 0
                    self.CURENT_PAYLOAD_INFO.clear()

                    return { 'type' : payload_type , 'chID' : chID , 'sum' : crc32_sum , 'size': payload_size , 'magic': magic , 'data' : payload}
            
        return None
    

    def Parse(self):
        
        return self._parse()
