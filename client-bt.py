# Get data sensors from STM32 platform with Bluetooth module
import signal
import click
import bluetooth as bt
import pandas as pd
import time

class Frame:
    def __init__(self):
        self.list = { "Horodatage": "0",
                      "Temperature": 0,
                      "Humidity": 0,
                      "Pressure": 0,
                      "Gas": 0,
                      "Luminosity": 0}

    def upgrade(self, horodatage, temperature, humidity, pressure, gas, luminosity):
        self.list["Horodatage"] = horodatage
        self.list["Temperature"] = temperature
        self.list["Humidity"] = humidity
        self.list["Pressure"] = pressure
        self.list["Gas"] = gas
        self.list["Luminosity"] = luminosity

    def dict(self):
        return [self.list]

def serializeDate(date):
    tmp = 'D='                    + \
          str(date.tm_year) + ':' + \
          str(date.tm_mon)  + ':' + \
          str(date.tm_mday) + ':' + \
          str(date.tm_wday) + ':' + \
          str(date.tm_hour) + ':' + \
          str(date.tm_min)  + ':' + \
          str(date.tm_sec)  + '\n'
    return tmp

def deserializeDate(msg_date):
    return msg_date

def extractFrame(msg):
    end = msg.find(',')
    if end == -1:
        end = msg.find('\n')
    id = msg[:1]
    msg_data = msg[2:end]
    return (end + 1), id, msg_data

def deserializeMsg(msg):
    nb_data = msg.count('=')
    index = 0
    while nb_data > 0:
        i, id, msg_data = extractFrame(msg[index:])
        index += i
        nb_data -= 1
        if id == "D":
            date = deserializeDate(msg_data)
        if id == "T":
            temperature = int(msg_data)
        if id == "P":
            pressure = int(msg_data)
        if id == "H":
            humidity = int(msg_data)
        if id == "L":
            # Receive voltage from uC (convert to uA) and Lux
            current = int(msg_data) / 68.0
            luminosity = int(pow(10, current / 10.0))
        if id == "G":
            gas = int(msg_data)
    return date, temperature, pressure, humidity, luminosity, gas

def get_msg(client_bt):
    c = 0
    msg_recv = b''
    while( c != b'\n'):
        c = client_bt.recv(1)
        msg_recv += c
    return msg_recv

@click.command()
@click.option("--init", "-i", is_flag=True)
def cli(init):
    client_bt = bt.BluetoothSocket(bt.RFCOMM)
    client_bt.connect(("98:D3:61:FD:63:8F", 1))
    data = Frame()
    db = pd.DataFrame()

    def exit(signum, frame):
        db.to_csv('file.csv')
        client_bt.close()
        exit()
    signal.signal(signal.SIGTERM, exit)

    if (init):
        client_bt.send("READY\r\n")
        date_send = time.localtime()
        msg_send = serializeDate(date_send)
        #print(msg_send)
        client_bt.send(msg_send.encode('ASCII'))

    while True:
        msg_recv = get_msg(client_bt)
        horodatage, temperature, pressure, humidity, luminosity, gas = deserializeMsg(msg_recv)
        data.upgrade(horodatage, temperature, humidity, pressure, gas, luminosity)
        db = db.append(data.dict(), ignore_index=True)
        print(db.tail(1))
        client_bt.send("ACK\r\n")

if __name__ == "__main__":
    cli()
