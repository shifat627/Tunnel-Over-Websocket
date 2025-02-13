import websockets,asyncio




from packet_utils import PayloadManager,PacketManager
    



                    





async def ws_connect():
        
    
        PkgMgr = PacketManager()
    
    
    #try:
        async with websockets.connect('ws://localhost/PTnlWsAgent') as ws:
            PayloadMgr = PayloadManager(ws)
            print("Connected")
            while True:
                # data = await ws.recv()
                
                # if isinstance(data,bytes):
                #     PkgMgr.feed(data)

                
                try:
                    data = await asyncio.wait_for(ws.recv(),3)
                    if isinstance(data,bytes):
                        PkgMgr.feed(data)
                except:
                    pass
                
                result = PkgMgr.Parse()
                
                if result is not None:
                    print(result)
                    await PayloadMgr.Parse(**result)



    # except Exception as Err:
    #     print(str(Err))

asyncio.run(ws_connect())