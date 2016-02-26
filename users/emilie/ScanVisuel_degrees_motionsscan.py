#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
This experiment was created using PsychoPy2 Experiment Builder (v1.82.00), Jeu  5 mar 15:39:16 2015
If you publish work using this script please cite the relevant PsychoPy publications
  Peirce, JW (2007) PsychoPy - Psychophysics software in Python. Journal of Neuroscience Methods, 162(1-2), 8-13.
  Peirce, JW (2009) Generating stimuli for neuroscience using PsychoPy. Frontiers in Neuroinformatics, 2:10. doi: 10.3389/neuro.11.010.2008
"""

from __future__ import division  # so that 1/3=0.333 instead of 1/3=0
from psychopy import visual, core, data, event, logging, sound, gui
from psychopy.constants import *  # things like STARTED, FINISHED
import numpy as np  # whole numpy lib is available, prepend 'np.'
from numpy import sin, cos, tan, log, log10, pi, average, sqrt, std, deg2rad, rad2deg, linspace, asarray
from numpy.random import random, randint, normal, shuffle
import os  # handy system and path functions
import serial
from visexpman.engine.vision_experiment import experiment
class PP_ScanVisuel_degrees_motionsscan(experiment.Stimulus):
    def stimulus_configuration(self):
        pass
        
    def calculate_stimulus_duration(self):
        self.duration=0
        
    def run(self):
        # Ensure that relative paths start from the same directory as this script
        _thisDir = self.machine_config.LOG_PATH
        os.chdir(_thisDir)

        # Store info about the experiment session
        expName = 'emi2'  # from the Builder filename that created this script
        expInfo = {'participant':'', 'session':'001'}
        expInfo['date'] = data.getDateStr()  # add a simple timestamp
        expInfo['expName'] = expName

        # Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
        filename = _thisDir + os.sep + 'data/%s_%s_%s' %(expInfo['participant'], expName, expInfo['date'])

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
        win=self.screen
        # store frame rate of monitor if we can measure it successfully
        expInfo['frameRate']=win.getActualFrameRate()
        if expInfo['frameRate']!=None:
            frameDur = 1.0/round(expInfo['frameRate'])
        else:
            frameDur = 1.0/60.0 # couldn't get a reliable measure so guess

        # Initialize components for Routine "blank"
        blankClock = core.Clock()
        blanktext = visual.TextStim(win=win, ori=0, name='blanktext',
            text=None,    font=u'Arial',
            pos=[0, 0], height=0.1, wrapWidth=None,
            color=u'white', colorSpace='rgb', opacity=1,
            depth=0.0)

        # Initialize components for Routine "trial"
        trialClock = core.Clock()
        grating = visual.GratingStim(win=win, name='grating',units='deg', 
            tex=u'sqr', mask=None,
            ori=1.0, pos=[0, 0], size=[260, 260], sf=1.0, phase=1.0,
            color=[1,1,1], colorSpace='rgb', opacity=1,
            texRes=512, interpolate=True, depth=0.0)

        # Initialize components for Routine "postblank"
        postblankClock = core.Clock()
        blanktext_2 = visual.TextStim(win=win, ori=0, name='blanktext_2',
            text=None,    font=u'Arial',
            pos=[0, 0], height=0.1, wrapWidth=None,
            color=u'white', colorSpace='rgb', opacity=1,
            depth=0.0)

        # Create some handy timers
        globalClock = core.Clock()  # to track the time since experiment started
        routineTimer = core.CountdownTimer()  # to track time remaining of each (non-slip) routine 

        # set up handler to look after randomisation of conditions etc
        trials = data.TrialHandler(nReps=20, method='sequential', 
            extraInfo=expInfo, originPath=None,
            trialList=data.importConditions(u'parameters_deg_motion.csv'),
            seed=None, name='trials')
        thisExp.addLoop(trials)  # add the loop to the experiment
        thisTrial = trials.trialList[0]  # so we can initialise stimuli with some values
        # abbreviate parameter names if possible (e.g. rgb=thisTrial.rgb)
        if thisTrial != None:
            for paramName in thisTrial.keys():
                exec(paramName + '= thisTrial.' + paramName)

        for thisTrial in trials:
            ser.write('e');
            currentLoop = trials
            # abbreviate parameter names if possible (e.g. rgb = thisTrial.rgb)
            if thisTrial != None:
                for paramName in thisTrial.keys():
                    exec(paramName + '= thisTrial.' + paramName)
            
            #------Prepare to start Routine "blank"-------
            t = 0
            blankClock.reset()  # clock 
            frameN = -1
            routineTimer.add(10.000000)
            # update component parameters for each repeat
            # keep track of which components have finished
            blankComponents = []
            blankComponents.append(blanktext)
            for thisComponent in blankComponents:
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            
            #-------Start Routine "blank"-------
            continueRoutine = True
            while continueRoutine and routineTimer.getTime() > 0:
                # get current time
                t = blankClock.getTime()
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # *blanktext* updates
                if t >= 0.0 and blanktext.status == NOT_STARTED:
                    # keep track of start time/frame for later
                    blanktext.tStart = t  # underestimates by a little under one frame
                    blanktext.frameNStart = frameN  # exact frame index
                    blanktext.setAutoDraw(True)
                if blanktext.status == STARTED and t >= (0.0 + (10-win.monitorFramePeriod*0.75)): #most of one frame period left
                    blanktext.setAutoDraw(False)
                
                # check if all components have finished
                if not continueRoutine:  # a component has requested a forced-end of Routine
                    routineTimer.reset()  # if we abort early the non-slip timer needs reset
                    break
                continueRoutine = False  # will revert to True if at least one component still running
                for thisComponent in blankComponents:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # check for quit (the Esc key)
                if endExpNow or event.getKeys(keyList=["escape"]):
                    break
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            #-------Ending Routine "blank"-------
            for thisComponent in blankComponents:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            
            #------Prepare to start Routine "trial"-------
            t = 0
            trialClock.reset()  # clock 
            frameN = -1
            routineTimer.add(10.000000)
            # update component parameters for each repeat
            grating.setOri(ori)
            # keep track of which components have finished
            trialComponents = []
            trialComponents.append(grating)
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
                
                # *grating* updates
                if t >= 0.0 and grating.status == NOT_STARTED:
                    # keep track of start time/frame for later
                    grating.tStart = t  # underestimates by a little under one frame
                    grating.frameNStart = frameN  # exact frame index
                    grating.setAutoDraw(True)
                if grating.status == STARTED and t >= (0.0 + (10-win.monitorFramePeriod*0.75)): #most of one frame period left
                    grating.setAutoDraw(False)
                if grating.status == STARTED:  # only update if being drawn
                    grating.setPhase(ph, '+', log=False)
                    grating.setSF(sf, log=False)
                
                
                # check if all components have finished
                if not continueRoutine:  # a component has requested a forced-end of Routine
                    routineTimer.reset()  # if we abort early the non-slip timer needs reset
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
            
            #------Prepare to start Routine "postblank"-------
            t = 0
            postblankClock.reset()  # clock 
            frameN = -1
            routineTimer.add(10.000000)
            # update component parameters for each repeat
            # keep track of which components have finished
            postblankComponents = []
            postblankComponents.append(blanktext_2)
            for thisComponent in postblankComponents:
                if hasattr(thisComponent, 'status'):
                    thisComponent.status = NOT_STARTED
            
            #-------Start Routine "postblank"-------
            continueRoutine = True
            while continueRoutine and routineTimer.getTime() > 0:
                # get current time
                t = postblankClock.getTime()
                frameN = frameN + 1  # number of completed frames (so 0 is the first frame)
                # update/draw components on each frame
                
                # *blanktext_2* updates
                if t >= 0.0 and blanktext_2.status == NOT_STARTED:
                    # keep track of start time/frame for later
                    blanktext_2.tStart = t  # underestimates by a little under one frame
                    blanktext_2.frameNStart = frameN  # exact frame index
                    blanktext_2.setAutoDraw(True)
                if blanktext_2.status == STARTED and t >= (0.0 + (10-win.monitorFramePeriod*0.75)): #most of one frame period left
                    blanktext_2.setAutoDraw(False)
                
                # check if all components have finished
                if not continueRoutine:  # a component has requested a forced-end of Routine
                    routineTimer.reset()  # if we abort early the non-slip timer needs reset
                    break
                continueRoutine = False  # will revert to True if at least one component still running
                for thisComponent in postblankComponents:
                    if hasattr(thisComponent, "status") and thisComponent.status != FINISHED:
                        continueRoutine = True
                        break  # at least one component has not yet finished
                
                # check for quit (the Esc key)
                if endExpNow or event.getKeys(keyList=["escape"]):
                    break
                
                # refresh the screen
                if continueRoutine:  # don't flip if this routine is over or we'll get a blank screen
                    win.flip()
            
            #-------Ending Routine "postblank"-------
            for thisComponent in postblankComponents:
                if hasattr(thisComponent, "setAutoDraw"):
                    thisComponent.setAutoDraw(False)
            thisExp.nextEntry()
        
