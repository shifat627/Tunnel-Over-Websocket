import struct
import zlib
import random
import os

import socket
class DummyTraffic:




    def generate_packet(self,session_id, payload,msg_type):
        magic = 0xDEADBEEF  # Fixed magic value
        payload_length = len(payload)
        crc32 = zlib.crc32(payload) & 0xFFFFFFFF  # Compute CRC32 checksum
        
        header = struct.pack('=L H L H L', magic, session_id, crc32, msg_type, payload_length)
        return header + payload
    

    def GenerateSet(self,Ip,port,msg):
        session_id = random.randint(0, 0xFFFF)
        conn_est = self.generate_packet(session_id,socket.inet_aton(Ip)+int.to_bytes(port,2,'big'),1)
        data_trans = self.generate_packet(session_id,msg.encode(),2)
        close_msg = self.generate_packet(session_id,b'',3)

        print(f'Packet Connection Establisted : {conn_est.hex()}')
        print(f'Data Trans: {data_trans.hex()}')
        print(f'Close Msg: {close_msg.hex()}')

dummy = DummyTraffic()

# Generate example traffic
packets = []
for i in range(5):
    session_id = random.randint(0, 0xFFFF)  # Random 2-byte session ID
    payload = os.urandom(random.randint(10, 50))  # Random payload (10-50 bytes)
    packet = dummy.generate_packet(session_id, payload,random.randint(0, 5))
    packets.append(packet)


packets.append(dummy.generate_packet(random.randint(0, 0xFFFF), b'',random.randint(0, 5)))

# Print packet data in hex format
for idx, packet in enumerate(packets):
    print(f"Packet {idx+1}: {packet.hex()}")


#dummy.GenerateSet('127.0.0.1',4444,'Hello World')
dummy.GenerateSet('192.168.0.101',4444,'Hello World,From Tunnel\n')