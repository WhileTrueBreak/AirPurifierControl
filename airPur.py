from asyncua import Client, ua
from multiprocessing import Process
from aioairctrl import CoAPClient
import asyncio
import time

APinfos = [
    ('172.31.1.200',41,1),
    ('172.31.1.201',42,2)]

class APClientProcess:
    def __init__(self, info):
        self.OpcUaHost = 'oct.tpc://172.31.1.236:4840/server/'
        self.ip = info[0]
        self.APclient = 0

        self.num = info[1]
        self.index = info[2]
        self.modeDict = {'AG': 0, 'S': 1, 'GT': 2, 'T': 3}
        self.boolDict = {'0': False, '1': True}

        self.invmodeDict = {v: k for k, v in self.modeDict.items()}
        self.invboolDict = {v: k for k, v in self.boolDict.items()}
        self.opcuaClient = Client(self.OpcUaHost)

        self.nodeDict = {}
    
    async def getClient(self, ip):
        client = await CoAPClient.create(host=ip)
        return client

    async def sendValue(self, node, value, type):
        if not node in self.nodeDict:
            self.nodeDict[node] = self.opcuaClient.get_node(node)
            print(f'{self.ip}\tadded {node} to dict')
        await self.nodeDict[node].set_value(value, type)

    async def getValue(self, node):
        if not node in self.nodeDict:
            self.nodeDict[node] = self.opcuaClient.get_node(node)
            print(f'{self.ip}\tadded {node} to dict')
        return await self.nodeDict[node].get_value()

    async def updateStatus(self, client, status):
        ACbtnlight = await self.getValue(f'ns={self.num};s=AP{self.index}c_BtnLight;')
        ACcl = await self.getValue(f'ns={self.num};s=AP{self.index}c_CL;')
        ACdspind = await self.getValue(f'ns={self.num};s=AP{self.index}c_DisplayIndex;')
        ACmode = await self.getValue(f'ns={self.num};s=AP{self.index}c_Mode;')
        ACname = await self.getValue(f'ns={self.num};s=AP{self.index}c_Name;')
        ACpwr = await self.getValue(f'ns={self.num};s=AP{self.index}c_PWR;')

        data = {}

        if ACbtnlight != self.boolDict[status['uil']]:
            print(f"{self.ip}\tupdating btn lights...")
            data['uil'] = self.invboolDict[ACbtnlight]
        if ACcl != status['cl']:
            print(f"{self.ip}\tupdating cl...")
            data['cl'] = ACcl
        if ACdspind != self.boolDict[status['ddp']]:
            print(f"{self.ip}\tupdating display lights...")
            data['ddp'] = self.invboolDict[ACdspind]
        if ACmode != self.modeDict[status['mode']]:
            print(f"{self.ip}\tupdating mode...")
            data['mode'] = self.invmodeDict[ACmode]
        if ACname != status['name']: 
            print(f"{self.ip}\tupdating name...")
            data['name'] = ACname
        if ACpwr != self.boolDict[status['pwr']]:
            print(f"{self.ip}\tupdating pwr...")
            data['pwr'] = self.invboolDict[ACpwr]
        
        if data:
            await client.set_control_values(data=data)
            print(f'{self.ip}\tupdated data.')
        
        await self.sendValue(f'ns={self.num};s=AP{self.index}d_PM25;', status['pm25'], ua.VariantType.Int32)
        await self.sendValue(f'ns={self.num};s=AP{self.index}d_Allergens;', status['iaql'], ua.VariantType.Int32)
        await self.sendValue(f'ns={self.num};s=AP{self.index}d_FilterStatus0;', status['fltsts0'], ua.VariantType.Int32)
        await self.sendValue(f'ns={self.num};s=AP{self.index}d_FilterStatus1;', status['fltsts1'], ua.VariantType.Int32)
        await self.sendValue(f'ns={self.num};s=AP{self.index}d_FilterStatus2;', status['fltsts2'], ua.VariantType.Int32)

    async def runAsync(self):
        self.APclient = await CoAPClient.create(host=self.ip)
        await self.opcuaClient.connect()
        while True:
            print(f'{self.ip}\tupdating status...')
            status = await self.APclient.get_status()
            await self.updateStatus(self.APclient, status[0])

def main():
    processes = [APClientProcess(info) for info in APinfos]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        *[process.runAsync() for process in processes]
    ))
    loop.close()
 
main()