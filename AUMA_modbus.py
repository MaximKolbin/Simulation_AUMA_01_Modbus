from pymodbus.server.sync import StartTcpServer, ModbusTcpServer, ModbusRtuFramer,ModbusSerialServer

from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import threading
#import concurrent.futures
#import concurrent.futures
# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)


device = 2
block = []
store = []
slaves ={}
init_classes = 1

class auma_ac01():

    def __init__(self):
        print("init")
        self.cmd = [] 
        self.status = []
        self.position = 0
        self.position_in = 0

    def input_conv(self,Input_r, index_r):
        temp = []
        pars = bin(Input_r[index_r])
        [temp.append(i) for i in pars]
        if len(temp)<18:
            index = 18-len(temp)
            for i in range(index):
                temp.insert(2,'0')
        return temp 

    def Input_r (self,values_I):
        self.status = self.input_conv(values_I, 0)

    def Holding_r (self, values_H):
        self.cmd = self.input_conv(values_H, 0)
        self.position_in = values_H[1]
        print(self.cmd)
        return self.cmd_auma()

    def cmd_auma(self):
        res=''     
        
        if self.cmd[13]=='1'and self.cmd[12]=='0' and  self.cmd[11]=='0' and self.cmd[10]=='0':
            print("Open") 
            if self.position<1000 :
                self.position = self.position + 100
                self.status[12]= '1'
                self.status[13]= '0'
            
        
        if self.cmd[13]=='0'and self.cmd[12]=='1' and  self.cmd[11]=='0' and self.cmd[10]=='0':
            print("close")
            if self.position>0 :
                self.position = self.position - 100
                self.status[13]= '1'
                self.status[12]= '0' 
         
        if self.cmd[13]=='0'and self.cmd[12]=='0' and  self.cmd[11]=='1' and self.cmd[10]=='0':
            print("ust")
            if self.position<self.position_in:
                self.position = self.position+100
                self.status[12]= '1'
                self.status[13]= '0'
                self.status[9]= '0'
                self.status[8]= '0'
            if self.position>self.position_in:
                self.position = self.position-100
                self.status[12]= '0'
                self.status[13]= '1'
                self.status[9]= '0'
                self.status[8]= '0'
            if self.position==self.position_in:
                self.status[12]= '0'
                self.status[13]= '0'

        if self.cmd[13]=='0'and self.cmd[12]=='0' and  self.cmd[11]=='0' and self.cmd[10]=='1':
            print("reset")


        if self.position==1000:
            self.status[8]= '1' 
            self.status[9]= '0' 
            self.status[12]= '0'
            self.status[13]= '0'

        if self.position==0:
            self.status[8] = '0' 
            self.status[9] = '1' 
            self.status[12] = '0'
            self.status[13] = '0'

        for i in self.status:
            res = res+i        
        status = int(res, base=2)          
        return status  

    def position_auma(self):
        return self.position


def run_server():
   
    block_H = [ModbusSequentialDataBlock(0x03E8, [0] * 0x03F7) for i in range(device)]
    block_I = [ModbusSequentialDataBlock(0x03E8, [0] * 0x03F7) for i in range(device)]
    for i in range(device) :
        store.append(ModbusSlaveContext(hr=block_H[i], ir= block_I[i]))
    slaves = {(i+1): store[i] for i in range(device)}

    for i in block_I:
        values_I = i.setValues(0x03E8, 516)
    context = ModbusServerContext(slaves=slaves, single=False)


    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #
    # If you don't set this or any fields, they are defaulted to empty strings.
    # ----------------------------------------------------------------------- #
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
    identity.ProductName = 'Pymodbus Server'
    identity.ModelName = 'Pymodbus Server'
    identity.MajorMinorRevision = '1.0'

    #StartTcpServer(context, identity=identity, address=('0.0.0.0', 5020))
    interval = 2
    auma_all = []
    #server = ModbusTcpServer(context, identity=identity,
    #                        address=('0.0.0.0', 5020))

    server =ModbusSerialServer(context, identity=identity, port='com1', framer=ModbusRtuFramer)                        
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    global init_classes
    if init_classes:
        for i in range(device):
            auma_all.append(auma_ac01())
        init_classes= 0  
    print(auma_all)
    


    loop = LoopingCall(f=update, auma_all = auma_all, I=block_I, H=block_H)
    loop.start(interval, now=True)
    reactor.run()

def main_r():
    with concurrent.futures.ProcessPoolExecutor() as executer:
        f2 = executer.submit(updat)
        f1 = executer.submit(run_server)
        
    #loop = LoopingCall(f=updatevalues, a=server)


    #loccop = LoopingCall(f=updat, I=block_I, H=block_H)
    #loop.start(interval, now=True)
    #reactor.run()

def update(auma_all,I,H):
    values_I = []
    values_H = []
    res=[]
    position = []
    j=0
    for i in I:
        values_I = i.getValues(0x03E8, count=10)
        auma_all[j].Input_r(values_I)
        j=j+1
    j=0
    for i in H:
        values_H = i.getValues(0x03E8, count=10)
        res.append(auma_all[j].Holding_r(values_H))
        position.append(auma_all[j].position_auma())
        j=j+1
    j=0  


    for i in I:
        i.setValues(0x03E8, res[j])
        i.setValues(0x03E9, position[j])
        j=j+1

    
    


   


def updatevalues(a):
    print("------------START----------")
    # contxt = a[1]
    rfuncode_H = 3
    rfuncode_I = 4
    wfuncode = 16
    values_I = []
    values_H = []
    address = 0x03E8
    auma_all = []
    for i in range(device):
        print (i)
        slave_id = i +1
        contxt = a.context[slave_id]
        values_I = contxt.getValues(rfuncode_I, address, count=5)
        values_H = contxt.getValues(rfuncode_H, address, count=5)
        auma_all.append(auma_ac01(values_I, values_H))

    for i in range(2):
        slave_id = i +1
        contxt = a.context[slave_id]   
        I = auma_all[i].status()
        H =  auma_all[i].status_H()
        contxt.c(wfuncode, address, H)
        print(I)

    #if values ==1 :
    #    contxt.setValues(wfuncode, address, values)
    #print(values)
    #values = [val+1 for val in values]
    #contxt.setValues(wfuncode, address, values)
    print("-------------END-------------")


if __name__ == "__main__":
    run_server()