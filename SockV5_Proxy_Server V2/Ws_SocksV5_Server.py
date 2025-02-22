import asyncio,sys,traceback,aiohttp
#from socket import inet_ntoa,gethostbyname,inet_ntop,AF_INET6,inet_pton,inet_aton

from packet_utils import PayloadManager,PacketManager,SockV5Handler



if len(sys.argv) != 3:
    print(f'{sys.argv[0]} <Ip:Port> <uid>')
    exit(0)


 
    
            
    


async def ws_connect():
        
    
    PkgMgr = PacketManager()
    SocksHandler = None
    session = aiohttp.ClientSession()

    try:
        
        async with session.ws_connect(f'ws://{sys.argv[1]}/tunnel?uid='+sys.argv[2]) as ws: 
            PayloadMgr = PayloadManager()
            conns , conns_lock = PayloadManager.GetConnListAndLock()
            SockV5Handler.SetParam(ws,conns,conns_lock)
            
            SocksHandler = asyncio.create_task(StartSocks5())
            
            print("Connected")
            
            async for data in ws:
                
                
                if data.type == aiohttp.WSMsgType.BINARY:
                    PkgMgr.feed(data.data)
                    
                elif data.type == aiohttp.WSMsgType.ERROR:
                    print('Error Detected')
                    break

                elif data.type == aiohttp.WSMsgType.CLOSE:
                    print('Closed Detected')
                    break
                
                
                result = PkgMgr.Parse()
                
                if result is not None:
                    #print(result)
                    await PayloadMgr.Parse(**result)


            print('Disconnected From Server')


    except Exception as Err:
        
        print(traceback.print_exc())

    finally:
        if SocksHandler is not None:
            SocksHandler.cancel()
        await session.close()

async def HandleSocksClient(reader,writer):
    socks5 = SockV5Handler(True,reader,writer)

    try:
        if (await socks5.HandShake(0)) != True:
            raise Exception('SockV5 Handshake Failed')
        

    except Exception as Err:
        print(traceback.print_exc())
    
    finally: # was Causing Disconnection error Error 
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