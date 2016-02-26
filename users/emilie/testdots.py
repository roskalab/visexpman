#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy2 Experiment Builder (v1.83.01), February 03, 2016, at 14:41
If you publish work using this script please cite the relevant PsychoPy publications
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
"""

from __future__ import division  # so that 1/3=0.333 instead of 1/3=0
from psychopy import locale_setup, visual, core, data, event, logging, sound, gui
from psychopy.constants import *  # things like STARTED, FINISHED
import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import sin, cos, tan, log, log10, pi, average, sqrt, std, deg2rad, rad2deg, linspace, asarray
from numpy.random import random, randint, normal, shuffle
import os  # handy system and path functions
import sys # to get file system encoding
import serial
from visexpman.engine.vision_experiment import experiment
class PP_dots(experiment.Stimulus):
    def stimulus_configuration(self):
        pass
        
    def calculate_stimulus_duration(self):
        self.duration=0
        
    def run(self):
        win = self.screen
        # Ensure that relative paths start from the same directory as this script
        _thisDir = self.machine_config.LOG_PATH
        os.chdir(_thisDir)

        # Store info about the experiment session
        expName = u'testdots'  # from the Builder filename that created this script
        expInfo = {'participant':'', 'session':'001'}
#        dlg = gui.DlgFromDict(dictionary=expInfo, title=expName)
#        if dlg.OK == False: core.quit()  # user pressed cancel
        expInfo['date'] = data.getDateStr()  # add a simple timestamp
        expInfo['expName'] = expName

        # Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
        filename = _thisDir + os.sep + u'data/%s_%s_%s' %(expInfo['participant'], expName, expInfo['date'])

        # An ExperimentHandler isn't essential but helps with data saving
        thisExp = data.ExperimentHandler(name=expName, version='',
            extraInfo=expInfo, runtimeInfo=None,
            originPath=None,
            savePickle=True, saveWideText=True,
            dataFileName=filename)
        #save a log file for detail verbose info
        logFile = logging.LogFile(filename+'.log', level=logging.EXP)
        logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

        endExpNow = False  # flag for 'escape' or other condition => quit the exp

        # Start Code - component code to be run before the window creation


        # Open serial port
        ser = serial.Serial('com1', 9600)

        # Setup the Window
        
        # store frame rate of monitor if we can measure it successfully
        expInfo['frameRate']=win.getActualFrameRate()
        if expInfo['frameRate']!=None:
            frameDur = 1.0/round(expInfo['frameRate'])
        else:
            frameDur = 1.0/60.0 # couldn't get a reliable measure so guess

        # Initialize components for Routine "trial"
        trialClock = core.Clock()
        dots = visual.DotStim(win=win, name='dots',units='deg', 
            nDots=100, dotSize=75,
            speed=0.001, dir=1.0, coherence=1.0,
            fieldPos=[0.0, 0.0], fieldSize=50,fieldShape='circle',
            signalDots='different', noiseDots='position',dotLife=100,
            color=[1.0,1.0,1.0], colorSpace='rgb', opacity=1,    depth=0.0)

        # Create some handy timers
        globalClock = core.Clock()  # to track the time since experiment started
        routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine 


        ser.write('e');
        #------Prepare to start Routine "trial"-------
        t = 0
        trialClock.reset()  # clock 
        frameN = -1
        timeTOT=900;
        routineTimer.add(timeTOT)
        # update component parameters for each repeat
        # keep track of which components have finished
        trialComponents = []
        trialComponents.append(dots)
        for thisComponent in trialComponents:
            if hasattr(thisComponent, 'status'):
                thisComponent.status = NOT_STARTED

        #-------Start Routine "trial"-------
        continueRoutine = True
        while continueRoutine and routineTimer.getTime() > 0:
            # get current time
            t = trialClock.getTime()
            frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
            # update/draw components on each frame
            
            # *dots* updates
            if t >= 0.0 and dots.status == NOT_STARTED:
                # keep track of start time/frame for later
                dots.tStart = t  # underestimates by a little under one frame
                dots.frameNStart = frameN  # exact frame index
                dots.setAutoDraw(True)
            if dots.status == STARTED and t >= (0.0 + (timeTOT-win.monitorFramePeriod*0.75)): #most of one frame period left
                dots.setAutoDraw(False)
            if dots.status == STARTED:  # only update if being drawn
                dots.setDir(0.075,'-', log=False)
            
            # check if all components have finished
            if not continueRoutine:  # a component has requested a forced-end of Routine
                break
            continueRoutine = False  # will revert to True if at least one component still running
            for thisComponent in trialComponents:
                if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                    continueRoutine = True
                    break  # at least one component has not yet finished
            
            # check for quit (the Esc key)
            if endExpNow or event.getKeys(keyList=["escape"]):
                break
            
            # refresh the screen
            if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                win.flip()

        #-------Ending Routine "trial"-------
        for thisComponent in trialComponents:
            if hasattr(thisComponent, "setAutoDraw"):
                thisComponent.setAutoDraw(False)
