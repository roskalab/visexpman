import pygame
import sys
import serial
################ Grating parameters ################
BAR_WIDTH = 4 #4,6,10,20#cm
SPEED = 1.0#cm/s, 10, 5, 1,0.4
DUTY_CYCLE = 0.5
ORIENTATION = 0#0,-180
DURATION = 10.0#s, -1: unlimited
################ End of parameters ################
PORT = '/dev/ttyUSB1'
SCREEN_SIZE = [47.6,26.9]
SCREEN_RESOLUTION = (800,600)
SCREEN_RESOLUTION = (1067,600)
SCREEN_RESOLUTION = (1920,1080)
SCREEN_FRQ = 60
FULLSCREEN = False
    
if __name__=='__main__':
    try:
        s=serial.Serial(PORT)
        s.setRTS(True)#Clearing acq pin
        serial_port=True
    except:
        print 'no camera triggering'
        serial_port=False
    pixel_size = SCREEN_SIZE[0]/SCREEN_RESOLUTION[0]
    bar_width = BAR_WIDTH/pixel_size
    spacing = bar_width//DUTY_CYCLE
    nstripes = int(SCREEN_RESOLUTION[0]/(spacing))
    pixel_speed = SPEED/pixel_size/SCREEN_FRQ
    nframes = DURATION*SCREEN_FRQ
    if ORIENTATION == 180:
        pixel_speed *= -1
        pygame.init()
    if FULLSCREEN:
        screen = pygame.display.set_mode((800,600),pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(SCREEN_RESOLUTION)
    pygame.mouse.set_visible(not FULLSCREEN)
    white = (255,255,255)
    black = (0,0,0)
    exit=False
    while True:
        screen.fill(black)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'escape'):
                exit=True
            elif (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'e'):
                pos = 0
                framect=0
                if serial_port:
                    s.setRTS(False)#Setting acq pin
                stimstop=False
                while (True):
                    # check for quit events
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'escape') :
                            exit=True
                            stimstop = True
                        elif (event.type == pygame.KEYDOWN and pygame.key.name(event.key) == 'a') or (DURATION > 0 and framect >= nframes):
                            stimstop=True
                    # erase the screen
                    screen.fill(black)
                    pos +=pixel_speed
                    if pos > spacing:
                        pos = 0
                    elif pos < -spacing:
                        pos = 0
                    for stripe in range(-2,nstripes+2):
                        position = pos+stripe*spacing
                        pygame.draw.rect(screen,white,(position,0,bar_width, SCREEN_RESOLUTION[1]))
                   # update the screen
                    pygame.display.flip()
                    framect+=1
                    if stimstop:
                        break
                if serial_port:
                    s.setRTS(True)#Clearing acq pin
        if exit:
            break
    if serial_port:
        s.close()
    pygame.quit()
    sys.exit()
