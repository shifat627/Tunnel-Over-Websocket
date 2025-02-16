from aiohttp import web
from uuid import uuid4


import logging

logging.basicConfig(level=logging.DEBUG) # To print log on terminal

class HandleWsClient:

    def __init__(self):
        self.ws_handle : dict[str,web.WebSocketResponse] = {}
        self.ws_connection_list : dict[str,web.WebSocketResponse] = {}

    def RegisterWsAgent(self,ws : web.WebSocketResponse ):
        ws_uuid = str(uuid4())
        self.ws_handle[ws_uuid] = ws
        return ws_uuid

    def RegisterWsMaster(self,uuid,master_ws : web.WebSocketResponse):
        
        if uuid in self.ws_handle and uuid not in self.ws_connection_list:
            self.ws_connection_list[uuid] = master_ws
        else:
            return False
        
        return self.ws_handle.get(uuid)


    

    def getC2(self,uuid):
        if uuid in self.ws_connection_list:
            return self.ws_connection_list[uuid]
        
        return None

    async def CleanUp(self):
        for ws in list(self.ws_connection_list.values()):
            await ws.close()

        for ws in list(self.ws_handle.values()):
            await ws.close()


    @property
    def GetAgentList(self):
        return list(self.ws_handle.keys())








async def StartUp(app : web.Application):
    app['WsManager'] = HandleWsClient()

async def ShutDown(app : web.Application):
    await app['WsManager'].CleanUp()










web_app = web.Application()

web_app.on_startup.append(StartUp)
web_app.on_shutdown.append(ShutDown)


#---------------------------------------------------------------------------------

async def PortTunnelAgent(req : web.Request):
    ws_handler = web.WebSocketResponse()
    await ws_handler.prepare(req)
    myUUID = ''
    ws_manager : HandleWsClient = req.app['WsManager']
    c2 = None


    try:
        myUUID = ws_manager.RegisterWsAgent(ws_handler)
        
        

        async for msg in ws_handler:

            

            if msg.type == web.WSMsgType.BINARY:
                if c2 is None or c2.closed == True:
                    c2 = ws_manager.getC2(myUUID)

                if c2 is not None and not c2.closed:
                    await c2.send_bytes(msg.data)

            if msg.type == web.WSMsgType.TEXT:
                if c2 is None or c2.closed == True:
                    c2 = ws_manager.getC2(myUUID)

                if c2 is not None and not c2.closed:

                    await c2.send_str(msg.data)
            
            if msg.type == web.WSMsgType.ERROR:
                break
                

    finally:
        
        if myUUID in ws_manager.ws_handle:
            del ws_manager.ws_handle[myUUID]
        if myUUID in ws_manager.ws_connection_list:
            await ws_manager.ws_connection_list[myUUID].close(message='Agent Disconnection')
            
        await ws_handler.close()

    return ws_handler

    


async def PortTunnelC2(req : web.Request):
    ws_handler = web.WebSocketResponse()
    await ws_handler.prepare(req)
    myUUID = req.query.get('uid','')
    
    ws_manager : HandleWsClient = req.app['WsManager']
    Agent = ws_manager.RegisterWsMaster(myUUID,ws_handler)
    
    if Agent != False and not Agent.closed:

        try:
            
            


            async for msg in ws_handler:

                #print(msg.data)

                if msg.type == web.WSMsgType.BINARY:
                    

                    if Agent is not None and not Agent.closed:
                        await Agent.send_bytes(msg.data)

                if msg.type == web.WSMsgType.TEXT:
                    

                    if Agent is not None and not Agent.closed:
                        await Agent.send_str(msg.data)
                
                if msg.type == web.WSMsgType.ERROR:
                    break
                    

        finally:
            if myUUID in ws_manager.ws_connection_list:
                del ws_manager.ws_connection_list[myUUID]
            

    return ws_handler



async def ListAgent(req : web.Request):
    
    return web.json_response(req.app['WsManager'].GetAgentList)

#----------------------------------------------------------------------------

web_app.router.add_get('/Ls',ListAgent)
web_app.router.add_get('/PTnlWsC2',PortTunnelC2)
web_app.router.add_get('/PTnlWsAgent',PortTunnelAgent)

if __name__ == '__main__':
    web.run_app(web_app,port=80)