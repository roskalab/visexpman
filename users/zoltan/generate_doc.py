import visexpman,inspect
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
if __name__ == "__main__":
    stimulus_class = utils.fetch_classes('visexpman.users.test', classname = 'TestStim', required_ancestors = visexpman.engine.vision_experiment.experiment.Stimulus,direct = False)
    f=open('r:\\temp\\ref.txt','w')
    for method in dir(stimulus_class[0][1]):
        if 'show' == method[:4] or 'moving' == method[:6] or 'receptive_field_explore'==method or 'increasing' in method:
            
            pars=[]
            for l in inspect.getsourcelines(getattr(stimulus_class[0][1],method))[0]:
                pars.append(l)
                if l[-3:]=='):\n':
                    break
            pars=''.join(pars)
            #pars=inspect.getsourcelines(getattr(stimulus_class[0][1],method))[0][0]
#            if '/r' not in pars:
#                pars=''.join([pars.split(',')[i]+',\n\t' if i%5==4 else pars.split(',')[i]+',' for i in range(len(pars.split(',')))])
#                pars=','.join(pars.split(',')[:-1])
            
            doc=getattr(stimulus_class[0][1],method).__doc__
            if doc!= None:
                f.write('====== {0} ======\r\n'.format(method))
                f.write('<code>{0}</code>\r\n'.format(pars))
                f.write(doc+'\r\n')
    f.close()
