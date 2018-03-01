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
U 1 1 5A736092
P 13950 6450
F 0 "U?" H 13350 7150 60  0000 C CNN
F 1 "Arduino_Uno" H 13850 5250 60  0000 C CNN
F 2 "" H 13900 6450 60  0000 C CNN
F 3 "" H 13900 6450 60  0000 C CNN
	1    13950 6450
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
Text Label 12300 7250 0    60   ~ 0
DAC0
Text Notes 6400 10150 0    60   ~ 0
Stimulus Start TTL Trigger
Text Notes 11400 7050 0    60   ~ 0
IOBoard's digital input test
Text Notes 7000 6750 0    60   ~ 0
Imaging frame timing signal
Text Notes 8350 1050 0    60   ~ 0
Stimulus frame timing
Text Notes 8600 1200 0    60   ~ 0
Block timing
Text Notes 9700 1050 0    60   ~ 0
Stimulus frame timing
Text Notes 10900 1300 0    60   ~ 0
Block timing
Text Notes 11100 6100 0    60   ~ 0
Timing signals to test with arduino digital input
Text Notes 8250 800  0    60   ~ 0
Shutter control
Text Notes 5500 8000 0    60   ~ 0
FM Waveform
Wire Wire Line
	4700 5850 1700 5850
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
	8850 2200 1500 2200
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
	13850 600  13850 2350
Wire Wire Line
	13850 5550 13850 4950
Wire Wire Line
	13850 4950 14650 4950
Wire Wire Line
	14650 4950 14650 500 
Wire Wire Line
	14650 500  1250 500 
Wire Wire Line
	1250 500  1250 2900
Wire Wire Line
	1250 2900 1800 2900
Wire Wire Line
	5000 6500 5000 6900
Wire Wire Line
	5000 6900 5600 6900
Wire Wire Line
	5600 6900 5600 6500
Wire Wire Line
	5150 6500 5150 7000
Wire Wire Line
	5150 7000 5750 7000
Wire Wire Line
	5750 7000 5750 6500
Wire Wire Line
	13200 7050 13200 7500
Wire Wire Line
	13200 7250 11600 7250
Connection ~ 13200 7250
Wire Wire Line
	5050 9950 5050 10200
Wire Wire Line
	5050 10200 8500 10200
Wire Wire Line
	8500 10200 8500 3850
Wire Wire Line
	8500 3850 8200 3850
Wire Wire Line
	5300 6500 5300 7100
Wire Wire Line
	5300 7100 12750 7100
Wire Wire Line
	12750 7100 12750 5850
Wire Wire Line
	12750 5850 13200 5850
Wire Wire Line
	5450 6500 5450 6800
Wire Wire Line
	5450 6800 8850 6800
Wire Wire Line
	8850 1400 9750 1400
Wire Wire Line
	8850 6800 8850 1400
Wire Wire Line
	8200 4150 8600 4150
Wire Wire Line
	8600 1250 8600 6000
Wire Wire Line
	8600 1250 9450 1250
Wire Wire Line
	8200 4450 8350 4450
Wire Wire Line
	8350 1100 8350 6150
Wire Wire Line
	8350 1100 9600 1100
Wire Wire Line
	13200 6300 11800 6300
Wire Wire Line
	11800 6300 11800 1100
Wire Wire Line
	11800 1100 10200 1100
Wire Wire Line
	13200 6450 11700 6450
Wire Wire Line
	11700 6450 11700 1200
Wire Wire Line
	11700 1200 10050 1200
Wire Wire Line
	9750 1400 9750 1550
Wire Wire Line
	9600 1100 9600 1550
Wire Wire Line
	9450 1250 9450 1550
Wire Wire Line
	8350 6150 13200 6150
Connection ~ 8350 4450
Wire Wire Line
	8600 6000 13200 6000
Connection ~ 8600 4150
Wire Wire Line
	9900 950  9900 1550
Wire Wire Line
	10050 1200 10050 1550
Wire Wire Line
	10200 1100 10200 1550
Wire Wire Line
	5000 5150 5000 4850
Wire Wire Line
	13200 6900 12950 6900
Wire Wire Line
	12950 6900 12950 8050
Wire Wire Line
	12950 8050 5500 8050
Wire Wire Line
	6050 6500 6050 7800
Wire Wire Line
	6050 7800 5200 7800
Wire Wire Line
	5200 7800 5200 8600
Wire Wire Line
	5900 6500 5900 7650
Wire Wire Line
	5900 7650 5050 7650
Wire Wire Line
	5050 7650 5050 8600
Text Notes 5050 7600 0    60   ~ 0
Emulated PMT signals
Wire Wire Line
	5200 9950 5200 10400
Wire Wire Line
	4550 10400 5200 10400
Wire Wire Line
	4550 700  4550 10400
Wire Wire Line
	4550 8250 5350 8250
Wire Wire Line
	5350 8250 5350 8600
Text Notes 4550 8200 0    60   ~ 0
Signal for syncronizing AI's of both USB 6003s and USB 6259
Wire Wire Line
	10500 1550 10500 700 
Wire Wire Line
	10500 700  4550 700 
Connection ~ 4550 8250
Wire Wire Line
	5500 8050 5500 8600
Wire Wire Line
	9900 2900 9900 3100
Wire Wire Line
	5750 5150 5750 4900
Wire Wire Line
	12750 4900 5750 4900
Wire Wire Line
	12750 2800 12750 4900
Wire Wire Line
	12750 3250 13200 3250
Wire Wire Line
	9900 3100 13200 3100
Wire Wire Line
	5800 9950 5800 10000
Wire Wire Line
	5800 10000 12250 10000
Wire Wire Line
	12250 10000 12250 3400
Wire Wire Line
	12250 3400 13200 3400
Wire Wire Line
	13200 2650 12250 2650
Wire Wire Line
	12250 2650 12250 3100
Connection ~ 12250 3100
Wire Wire Line
	12750 2800 13200 2800
Connection ~ 12750 3250
Wire Wire Line
	13200 2950 12900 2950
Wire Wire Line
	12900 2950 12900 3400
Connection ~ 12900 3400
Text Notes 11100 3350 0    60   ~ 0
Controlling PFI inputs of DAQ devices
Wire Wire Line
	5650 8600 5650 8250
Wire Wire Line
	5650 8250 11600 8250
Wire Wire Line
	11600 8250 11600 7250
Wire Wire Line
	9150 2900 9150 3150
Wire Wire Line
	9150 3150 8000 3150
Wire Wire Line
	8000 3150 8000 950 
Wire Wire Line
	8000 950  9900 950 
Text Notes 5500 1600 0    60   ~ 0
Timing signals generated by different devices: arduino, usb-uart, daq
Text Notes 4800 7100 0    60   ~ 0
Scanner signals
Wire Wire Line
	6200 6500 6200 7350
Wire Wire Line
	6200 7350 4550 7350
Connection ~ 4550 7350
Wire Wire Line
	13150 6600 9050 6600
Wire Wire Line
	9050 6600 9050 7500
Wire Wire Line
	9050 7500 4300 7500
Wire Wire Line
	4300 7500 4300 6600
Wire Wire Line
	4300 6600 1350 6600
Wire Wire Line
	1350 6600 1350 7200
Text Notes 950  6550 0    60   ~ 0
Camera trigger
Wire Wire Line
	5800 8600 5800 8450
Wire Wire Line
	5800 8450 4050 8450
Wire Wire Line
	4050 8450 4050 4850
Wire Wire Line
	4050 4850 5000 4850
Wire Wire Line
	10350 1550 10350 800 
Wire Wire Line
	10350 800  9150 800 
Wire Wire Line
	9150 800  9150 1550
Text Notes 9200 800  0    60   ~ 0
Laser/LED control signal
$EndSCHEMATC
