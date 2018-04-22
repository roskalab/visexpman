EESchema Schematic File Version 2
LIBS:power
LIBS:device
LIBS:transistors
LIBS:conn
LIBS:linear
LIBS:regul
LIBS:74xx
LIBS:cmos4000
LIBS:adc-dac
LIBS:memory
LIBS:xilinx
LIBS:microcontrollers
LIBS:dsp
LIBS:microchip
LIBS:analog_switches
LIBS:motorola
LIBS:texas
LIBS:intel
LIBS:audio
LIBS:interface
LIBS:digital-audio
LIBS:philips
LIBS:display
LIBS:cypress
LIBS:siliconi
LIBS:opto
LIBS:atmel
LIBS:contrib
LIBS:valves
LIBS:test_station_components
LIBS:test_station-cache
EELAYER 25 0
EELAYER END
$Descr A3 16535 11693
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L DELL_Precision_3620 Stimulus~computer
U 1 1 5A73450C
P 2450 3200
F 0 "Stimulus computer" H 2050 3950 60  0000 C CNN
F 1 "DELL_Precision_3620" H 2450 2850 60  0000 C CNN
F 2 "" H 2450 3200 60  0000 C CNN
F 3 "" H 2450 3200 60  0000 C CNN
	1    2450 3200
	1    0    0    -1  
$EndComp
$Comp
L DELL_Precision_3620 Imaging~computer
U 1 1 5A7345F9
P 2950 7750
F 0 "Imaging computer" H 2550 8500 60  0000 C CNN
F 1 "DELL_Precision_3620" H 2950 7400 60  0000 C CNN
F 2 "" H 2950 7750 60  0000 C CNN
F 3 "" H 2950 7750 60  0000 C CNN
	1    2950 7750
	1    0    0    -1  
$EndComp
$Comp
L camera Webcam
U 1 1 5A7346D9
P 950 3200
F 0 "Webcam" H 800 3450 60  0000 C CNN
F 1 "camera" H 1000 2950 60  0000 C CNN
F 2 "" H 750 3350 60  0000 C CNN
F 3 "" H 750 3350 60  0000 C CNN
	1    950  3200
	-1   0    0    -1  
$EndComp
$Comp
L camera Eye~Camera
U 1 1 5A7347A2
P 1100 7300
F 0 "Eye Camera" H 950 7550 60  0000 C CNN
F 1 "camera" H 1150 7050 60  0000 C CNN
F 2 "" H 900 7450 60  0000 C CNN
F 3 "" H 900 7450 60  0000 C CNN
	1    1100 7300
	-1   0    0    1   
$EndComp
$Comp
L USB_6259 U?
U 1 1 5A734B97
P 5100 5800
F 0 "U?" H 5450 6050 60  0000 C CNN
F 1 "USB_6259" H 5100 4100 60  0000 C CNN
F 2 "" H 5100 5800 60  0000 C CNN
F 3 "" H 5100 5800 60  0000 C CNN
	1    5100 5800
	0    -1   1    0   
$EndComp
$Comp
L USB_6003 U?
U 1 1 5A734F9D
P 5150 9300
F 0 "U?" H 5500 9550 60  0000 C CNN
F 1 "USB_6003" H 5150 7600 60  0000 C CNN
F 2 "" H 5150 9300 60  0000 C CNN
F 3 "" H 5150 9300 60  0000 C CNN
	1    5150 9300
	0    -1   -1   0   
$EndComp
$Comp
L usb-uart U?
U 1 1 5A735D80
P 7600 4200
F 0 "U?" H 7300 4850 60  0000 C CNN
F 1 "usb-uart" H 7550 3800 60  0000 C CNN
F 2 "" H 7700 4200 60  0000 C CNN
F 3 "" H 7700 4200 60  0000 C CNN
	1    7600 4200
	1    0    0    -1  
$EndComp
$Comp
L Arduino_Uno U?
U 1 1 5A7361E1
P 13950 3250
F 0 "U?" H 13350 3950 60  0000 C CNN
F 1 "Arduino_Uno" H 13850 2050 60  0000 C CNN
F 2 "" H 13900 3250 60  0000 C CNN
F 3 "" H 13900 3250 60  0000 C CNN
	1    13950 3250
	1    0    0    -1  
$EndComp
Text Notes 13650 10900 0    60   ~ 0
Test Station Wiring Design
Wire Wire Line
	1700 5850 1700 7150
Wire Wire Line
	1700 7150 2300 7150
Wire Wire Line
	1500 7300 2300 7300
Wire Wire Line
	4750 9250 2000 9250
Wire Wire Line
	2000 9250 2000 7900
Wire Wire Line
	2000 7900 2300 7900
Wire Wire Line
	7050 4100 1400 4100
Wire Wire Line
	1400 4100 1400 3350
Wire Wire Line
	1400 3350 1800 3350
Wire Wire Line
	1800 3200 1350 3200
Wire Wire Line
	1500 2200 1500 2600
Wire Wire Line
	1500 2600 1800 2600
Wire Wire Line
	1800 2750 1350 2750
Wire Wire Line
	1350 2750 1350 600 
Wire Wire Line
	1350 600  13850 600 
Wire Wire Line
	14650 500  1250 500 
Wire Wire Line
	1250 500  1250 2900
Wire Wire Line
	1250 2900 1800 2900
Wire Wire Line
	4700 5850 1700 5850
Wire Wire Line
	13850 600  13850 2350
Wire Wire Line
	8850 2200 1500 2200
Wire Wire Line
	9150 2900 9150 10950
Wire Wire Line
	9150 10950 5050 10950
Wire Wire Line
	5050 10950 5050 9950
Text Label 6450 10950 0    60   ~ 0
Stim_trigger_to_microscope
Wire Wire Line
	5200 9950 5200 10800
Wire Wire Line
	4600 10800 8650 10800
Wire Wire Line
	8650 10800 8650 1300
Wire Wire Line
	8650 1300 9600 1300
Wire Wire Line
	9450 1550 9450 1400
Wire Wire Line
	9450 1400 8800 1400
Wire Wire Line
	8800 1400 8800 3050
Wire Wire Line
	8800 3050 9150 3050
Connection ~ 9150 3050
Wire Wire Line
	9600 1300 9600 1550
Text Label 6400 10800 0    60   ~ 0
Simulated_microscope_frame_sync
Wire Wire Line
	9300 2900 9300 3150
Wire Wire Line
	9300 3150 8500 3150
Wire Wire Line
	8500 3150 8500 1150
Wire Wire Line
	8500 1150 9750 1150
Wire Wire Line
	9750 1150 9750 1550
Text Label 8550 1150 0    60   ~ 0
Stim_frame_timing
Wire Wire Line
	9450 2900 9450 3250
Wire Wire Line
	9450 3250 8350 3250
Wire Wire Line
	8350 3250 8350 1000
Wire Wire Line
	8350 1000 9900 1000
Wire Wire Line
	9900 1000 9900 1550
Text Label 8700 1000 0    60   ~ 0
Stim_block_timing
Wire Wire Line
	10200 9950 6100 9950
Wire Wire Line
	10200 2900 10200 9950
Wire Wire Line
	8200 3700 10200 3700
Connection ~ 10200 3700
Wire Wire Line
	8200 4450 8400 4450
Wire Wire Line
	8400 4450 8400 8000
Wire Wire Line
	8400 8000 5350 8000
Wire Wire Line
	5350 8000 5350 8600
Wire Wire Line
	8200 4150 8500 4150
Wire Wire Line
	8500 4150 8500 8100
Wire Wire Line
	5500 8100 5500 8600
Text Label 6000 8000 0    60   ~ 0
Stim_frame_timing
Text Label 6000 8100 0    60   ~ 0
Stim_block_timing
Text Notes 5600 7800 0    60   ~ 0
Main_ui records timing signals
Wire Wire Line
	5650 8200 5650 8600
Wire Wire Line
	5800 8300 5800 8600
Text Label 6000 8200 0    60   ~ 0
Stim_frame_timing
Text Label 6000 8300 0    60   ~ 0
Stim_block_timing
Text Notes 6100 10600 0    60   ~ 0
MES signals simulated by Imaging computer
Text Notes 8100 850  0    60   ~ 0
Stim records timing signals including stimulus timing
Wire Wire Line
	8500 8100 5500 8100
Wire Wire Line
	5650 8200 9600 8200
Wire Wire Line
	9600 8200 9600 2900
Wire Wire Line
	5800 8300 9750 8300
Wire Wire Line
	9750 8300 9750 2900
Wire Wire Line
	4600 10800 4600 8400
Wire Wire Line
	4600 8400 5950 8400
Wire Wire Line
	5950 8400 5950 8600
Connection ~ 5200 10800
Wire Wire Line
	6100 8600 6100 8400
Wire Wire Line
	6100 8400 11800 8400
Wire Wire Line
	11800 8400 11800 3100
Wire Wire Line
	11800 3100 13200 3100
Wire Wire Line
	13200 3250 11950 3250
Wire Wire Line
	11950 3250 11950 8500
Wire Wire Line
	11950 8500 6250 8500
Wire Wire Line
	6250 8500 6250 8600
Text Label 6350 8400 0    60   ~ 0
Stim_frame_timing
Text Label 6350 8500 0    60   ~ 0
Stim_block_timing
Wire Wire Line
	9300 1550 9300 1450
Wire Wire Line
	9300 1450 8000 1450
Wire Wire Line
	8000 1450 8000 2950
Wire Wire Line
	8000 2950 13200 2950
Text Label 11050 2950 0    60   ~ 0
IOboard_digital_input_timing_calibration
Wire Wire Line
	13200 3400 12950 3400
Wire Wire Line
	12950 3400 12950 2800
Wire Wire Line
	12950 2800 13200 2800
Text Label 12300 2800 0    60   ~ 0
Stim_block_timing
Wire Wire Line
	5000 6500 5000 6800
Wire Wire Line
	5000 6800 5600 6800
Wire Wire Line
	5600 6800 5600 6500
Text Label 5050 6800 0    60   ~ 0
scanner_x
Wire Wire Line
	5150 6500 5150 6700
Wire Wire Line
	5150 6700 5750 6700
Wire Wire Line
	5750 6700 5750 6500
Text Label 5200 6700 0    60   ~ 0
scanner_y
Wire Wire Line
	5300 6500 5300 6600
Wire Wire Line
	5900 6600 4500 6600
Wire Wire Line
	4500 6600 4500 700 
Wire Wire Line
	4500 700  10050 700 
$Comp
L USB_6003 U?
U 1 1 5A735086
P 9250 2250
F 0 "U?" H 9600 2500 60  0000 C CNN
F 1 "USB_6003" H 9250 550 60  0000 C CNN
F 2 "" H 9250 2250 60  0000 C CNN
F 3 "" H 9250 2250 60  0000 C CNN
	1    9250 2250
	0    -1   -1   0   
$EndComp
Wire Wire Line
	10050 700  10050 1550
Text Label 8550 700  0    60   ~ 0
retinal_2p_frame_timing
Wire Wire Line
	5900 6500 5900 6600
Connection ~ 5300 6600
Text Notes 4950 5000 0    60   ~ 0
Retinal two photon microscope
Wire Wire Line
	13200 3700 12550 3700
Wire Wire Line
	12550 3700 12550 6600
Wire Wire Line
	12550 6600 6650 6600
Wire Wire Line
	6650 6600 6650 6500
Text Label 6900 6600 0    60   ~ 0
IOBoard_waveform_generator
$EndSCHEMATC
