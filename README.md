# Basic Tunneling Over Websocket + SocksV5

## Usage

First , You Must Run the **frontEnd_Waiter_Server.py**
This is the http Server. You can host any where you want. Just Change the websocket url in the file accordingly to url of the hosted site

> run the Agent.py on the target PC. It will connect back to the web server

> send a get request to <webserver_url.com>/Ls , to list connected agent and their UID

> run the Ws_SocksV5_Server.py on the local pc. It will connect to web server and start a socks5 proxy server on the PC.



