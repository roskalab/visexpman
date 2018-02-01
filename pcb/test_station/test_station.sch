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
L DELL_Precision_3620 Stimulus
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
L DELL_Precision_3620 Imaging
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
L camera Eye
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
Text Notes 13650 10900 0    60   ~ 0
Test Station Wiring Design
$EndSCHEMATC
