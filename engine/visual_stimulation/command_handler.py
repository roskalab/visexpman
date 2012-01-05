import socket
import os
import time
import re
import PyQt4.QtCore as QtCore
#import visexpman.engine.hardware_interface.udp_interface as network_interface
import stimulation_control as experiment_control
import experiment
import visexpman.engine.hardware_interface.instrument as instrument
import visexpman.engine.hardware_interface.motor_control as motor_control
command_extract = re.compile('SOC(.+)EOC') # a command is a string starting with SOC and terminated with EOC (End Of Command)
parameter_extract = re.compile('EOC(.+)EOP') # an optional parameter string follows EOC terminated by EOP. In case of binary data EOC and EOP should be escaped.
#TODO: at experiment start reload all modules so that user could edit them during runtime
class CommandHandler(object):
    '''
    Responsible for interpreting incoming commands and calling the necessary functions
    '''
    def __init__(self, config, caller):
        '''
        TBD
        '''        
        self.machine_config = config
        self.caller = caller
        self.config = config
        #Initialize slected experiment config index
        for i in range(len(self.caller.experiment_config_list)):
            if self.caller.experiment_config_list[i][1].__name__ == self.config.EXPERIMENT_CONFIG:
                self.selected_experiment_config_index = i
        #Experiment counter will be used to identify each experiment (logging,....)
        self.experiment_counter = 0
        
        self.presentinator_interface = {
                                        'command' : '', 
                                        'color' : None                                        
                                        }
        
    def process_command_buffer(self):
        '''
        Parsing all the commands in the command buffer
        '''
        result = ''
        while not self.caller.command_queue.empty():
            result += '\n' + str(self.parse(self.caller.command_queue.get()))
        while not self.caller.mes_response_queue.empty():
            result += '\n' + self.caller.mes_response_queue.get()
        while not self.caller.from_gui_queue.empty():            
            result += '\n' + str(self.parse(self.caller.from_gui_queue.get()))
        self.caller.command_buffer = []
        self.caller.screen_and_keyboard.message += result

    def select_experiment(self, par):
        '''
        Selects experiment config based on keyboard command and instantiates the experiment config class
        '''
        self.selected_experiment_config_index = int(par)
        return 'selected experiment: ' + str(par) + ' '

    def execute_experiment(self, par):        
        #Experiment control class is always (re)created so that the necessary hardware initializations could take place
        self.caller.experiment_control = experiment_control.ExperimentControl(self.config, self.caller, par)
        #Run experiment
        self.caller.experiment_control.run_experiment()
        #Clean up experiment
        self.caller.experiment_control.finish_experiment()
        self.experiment_counter += 1
        return 'experiment executed'

    def bullseye(self, par):
        self.caller.screen_and_keyboard.show_bullseye = not self.caller.screen_and_keyboard.show_bullseye
        return 'bullseye'

    def color(self, par):
        self.presentinator_interface['command'] = 'color'
        self.presentinator_interface['color'] = int(par)
        return 'color'
        
    def filterwheel(self, par):        
        if len(par) != 2:
            raise RuntimeError('Invalid filter id and position')
        filterwheel_id = int(par[0])
        filter = int(par[1])
#        #Here comes an init-set-close sequence
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):            
            filterwheel = instrument.Filterwheel(self.config, self.caller, id = filterwheel_id)
            filterwheel.set(filter)
            if os.name == 'nt':
                filterwheel.release_instrument()
        return 'filterwheel ' + par

    def stage(self,par):
        '''
        read stage:
            command: SOCstageEOCreadEOP
            response: SOCstageEOCx,y,zEOP
        set stage:
            command: SOCstageEOCset,y,zEOP
            response: SOCstageEOC<status>,x,y,zEOP, <status> = OK, error
        '''
        
        if 'read' in par or 'set' in par or 'origin' in par:
            stage = motor_control.AllegraStage(self.config, self.caller)
            position = stage.read_position()
            self.caller.to_gui_queue.put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
            if 'origin' in par:
                self.caller.stage_origin = position                
            if 'set' in par:
                new_position = par.split(',')[1:]
                new_position = numpy.array([float(new_position[0]), float(new_position[1]), float(new_position[2])])
                reached = stage.move(new_position)
                position = stage.read_position()
                self.caller.to_gui_queue.put('SOCstageEOC{0},{1},{2}EOP'.format(position[0], position[1], position[2]))
            stage.release_instrument()            
        return str(position)
        
    def hide_menu(self, par):
        self.caller.screen_and_keyboard.hide_menu = not self.caller.screen_and_keyboard.hide_menu
        if self.caller.screen_and_keyboard.hide_menu:
            return ''
        else:
            return 'menu is unhidden'

    def abort_experiment(self, par):
        return 'abort_experiment'
        
    def echo(self, par):
        self.caller.mes_command_queue.put('SOCechoEOCvisexpmanEOP')
        self.caller.to_gui_queue.put('SOCechoEOCvisexpmanEOP')
        return 'echo'
        
    def set_measurement_id(self, par): #temporary, this command will be sent by GUI
        self.caller.mes_command_queue.put('SOCsetIDEOCvalami{0}EOP'.format(time.time()))
        return 'set_measurement_id'

    def quit(self, par):
        self.caller.loop_state = 'end loop'
        return 'quit'

    def parse(self,  command_buffer,  state = 'unspecified'):
        '''
        Incoming string stream is parsed into commands depending on software state. When stimulation is running, incoming string is discarded
        '''        
        result  = None        
        if len(command_buffer) > 6: #SOC + EOC + 1 character is at least present in a command
            cmd = command_extract.findall(command_buffer)
            command_buffer_newline_replaced = command_buffer.replace('\n',  '<newline>')
            par = parameter_extract.findall(command_buffer_newline_replaced) #par is not at the beginning of the buffer             
            if len(par)>0:
                par = [par[0].replace('<newline>',  '\n')]
            if len(par)>0:
                par = par[0]
            if len(cmd) > 0: #To avoid crash, dummy commands are sent by Presentinator.
                if hasattr(self, cmd[0]):
                    result=getattr(self, cmd[0])(par) # call the selected function with the optional parameter
                else:
                    #If no function belong to the command, just return it. During experiment, keyboard commands are passed to command buffer this way.
                    result = cmd[0]
            else:
                result = ''
            self.caller.log.info('Command handler: ' + result)
        return result

class CommandSender(QtCore.QThread):
    def __init__(self, config, caller, commands):
        self.config = config
        self.caller = caller
        self.commands = commands
        QtCore.QThread.__init__(self)
        
    def send_command(self, command):
        self.caller.command_queue.put(command)
        
    def run(self):
        for command in self.commands:
            time.sleep(command[0])
            self.send_command(command[1])            

    def close(self):
        self.terminate()
        self.wait()

if __name__ == "__main__":
    pass
