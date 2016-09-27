import numpy,time
import pdb
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
import visexpA.engine.datahandlers.hdf5io as hdf5io


class NaturalBarsConfig1(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPEED = [800, 400,1500.0]#um/s
        self.SPEED = [400]
        self.REPEATS = 2 #5
        self.DIRECTIONS = [0] #range(0,360,90)
        self.DURATION = 5
        self.BACKGROUND_TIME = 0
        self.BACKGROUND_COLOR = 0.5
        self.ALWAYS_FLY_IN_OUT = not False
        self.runnable = 'NaturalBarsExperiment1'
        self._create_parameters_from_locals(locals())

class NaturalBarsExperiment1(experiment.Experiment):
    def prepare(self):
        self.stimulus_duration = self.experiment_config.DURATION
        
    def run(self):
        self.show_fullscreen(duration = self.experiment_config.DURATION, color =  self.experiment_config.BACKGROUND_COLOR)

class DottestConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        import tables, pdb, os
        from contextlib import closing
        self.FILENAME='/mnt/databig/Dense_Balls_Basel_Variables.mat'
        vnames = ['DOT_COORDINATES','DOT_DIAMETERS','DOT_COLORS']
        if not os.path.exists(self.FILENAME+'_cached.hdf5'):
            st = time.time()
            with closing(tables.open_file(self.FILENAME)) as t1:
                self.DOT_COORDINATES = t1.root.Traj_px.read()
                self.DOT_DIAMETERS = t1.root.Radius.read()*2
                self.DOT_COLORS =  numpy.tile(t1.root.Gscale.read()[:,0],[3,1]).T
            drop_inactive_dots = 1
            if drop_inactive_dots:
                inactive = numpy.where(self.DOT_COORDINATES.sum(axis=0)==0)
                maxrad = self.DOT_DIAMETERS.max()
                self.DOT_COORDINATES1 = []
                for d1 in self.DOT_COORDINATES.T:
                    d1[numpy.where(d1.sum(axis=0))] -= maxrad
                    self.DOT_COORDINATES1.append(utils.rc(d1))
                self.DOT_COORDINATES = self.DOT_COORDINATES1
                # show_shapes does not support variable number of shapes per frame, do not drop inactive dots but shift them out of screen
                #self.DOT_COORDINATES = [utils.rc(d1[numpy.where(d1.sum(axis=1)>0)]) for d1 in self.DOT_COORDINATES.T]
            else:
                self.DOT_COORDINATES = [utils.rc(d1) for d1 in self.DOT_COORDINATES.T]
            print('Prepare lasted {0}s'.format(time.time()-st))
            with closing(hdf5io.Hdf5io(self.FILENAME+'_cached.hdf5', filelocking=0)) as t1:
                [setattr(t1,v1,getattr(self,v1)) for v1 in vnames]
                t1.save(vnames)
        else:
            st = time.time()
            with closing(hdf5io.Hdf5io(self.FILENAME + '_cached.hdf5', filelocking=0)) as t1:
                t1.load(vnames)
                [setattr(self, v1, getattr(t1, v1)) for v1 in vnames]
            print('Prepare lasted {0}s'.format(time.time() - st))
        self.runnable = 'DottestExperiment'
        self._create_parameters_from_locals(locals())
        
class DottestExperiment(experiment.Experiment):
    def run(self):
        test = 0
        if test:
            duration=60
            nframes=duration*60
            ndots=200
            dot_diameters=40+10*numpy.random.random(nframes*ndots)
            positions=utils.rc((
                        numpy.random.random(ndots)*800-400,
                        numpy.random.random(ndots)*800-400,
    #                    numpy.array([0,100, 0, 100]),
    #                    numpy.array([0,100, 100, 0])
                        ))

            dot_positions=numpy.tile(positions,nframes)
            for i in range(nframes*ndots):
                dot_positions[i*ndots:(i+1)*ndots]['row']+=numpy.random.random()*500-250
                dot_positions[i*ndots:(i+1)*ndots]['col']+=numpy.random.random()*500-250
            t0=time.time()
            pdb.set_trace()
            self.show_dots(dot_diameters, dot_positions, ndots)
            print t0-time.time()
        else:
            # this version calls show_dots for each frame, cannot achieve good display framerate
            for dc in self.experiment_config.DOT_COORDINATES:
                self.show_dots(self.experiment_config.DOT_DIAMETERS, dc,
                           len(self.experiment_config.DOT_DIAMETERS), color=self.experiment_config.DOT_COLORS)
if __name__ == "__main__":
    from visexpman.engine.visexp_app import stimulation_tester
    import traceback
    from visexpA.engine.generic.introspect import full_exc_info
    try:
        stimulation_tester('zoltan', 'StimulusDevelopment', 'DottestConfig')
    except:
        traceback.print_exc()
        pdb.post_mortem(full_exc_info()[2])
        raise
    finally:
        pass

