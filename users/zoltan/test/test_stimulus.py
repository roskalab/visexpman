import visexpman.engine.visexp_runner as visexp_runner
import visexpman.engine.visual_stimulation.command_handler as command_handler

commands = [
                    [0.01,'SOCexecute_experimentEOC'],                     
                    [0.01,'SOCquitEOC'], 
                    ]
config_name = 'VRWT'
v = visexp_runner.VisExpRunner('zoltan', config_name)
cs = command_handler.CommandSender(v.config, v, commands)
cs.start()
v.run_loop()
cs.close()