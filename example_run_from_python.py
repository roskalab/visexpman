#!/usr/bin/python
"""
Created on Wed Feb  3 11:14:02 2016

@author: rolandd

Example how to run the app from python.
"""
import visexpman.engine.visexp_app as app

# Run in debug mode:
app.run_application_py(user = 'roland',
            config = 'MEAConfigDebug',
            user_interface_name = 'stim',
            single_file = 'pilot03_cell_classification')
