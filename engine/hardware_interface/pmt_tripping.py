import logging
import pyvisa
from visexpman.engine.generic import utils

class PMTTripping(object):
    def __init__(self, logfile, notif_email):
        self.logfile = logfile
        self.notif_email = notif_email
        self.rm = pyvisa.ResourceManager()
        logging.basicConfig(format='%(asctime)s %(levelname)s\t%(message)s', level=logging.INFO, handlers=[logging.FileHandler(self.logfile), logging.StreamHandler()])
        devlist = self.rm.list_resources()
        logging.info(devlist)
        if devlist:
            try:
                self.inst = self.rm.open_resource(devlist[0])
                logging.info(self.inst.query("*IDN?"))
            except pyvisa.VisaIOError:
                logging.error('VisaIOError exception')
        else:
            logging.error('No PMT device found!')
     
    def has_tripped(self):
        devlist = self.rm.list_resources()
        if devlist:
            try:
                self.inst = self.rm.open_resource(devlist[0])
                return self.inst.query("SENSe:CURRent:DC:PROTection:TRIPped?") == "1"
            except pyvisa.VisaIOError:
                logging.error('VisaIOError exception')
                return False
                
        else:
            logging.error('No PMT device found!')
            return False
        
    def handle_tripping(self):
        logging.info("PMT tripping signal clearing")
        utils.sendmail(self.notif_email, 'PMT tripping', 'PMT tripping has been detected')
        try:
            self.inst.query("SENSe:CURRent:DC:PROTection:CLEar") #clear tripping signal
            self.inst.query("SENSe:FUNCtion:OFF") #turn PMT power off
            import time
            time.sleep(5)
            self.inst.query("SENSe:FUNCtion:ON") #turn PMT power on
           
        except pyvisa.VisaIOError:
            logging.error("VisaIOError exception")
             
        