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
EELAYER 25 0
EELAYER END
$Descr A4 11693 8268
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
L LM386 U1
U 1 1 5A609BF0
P 4550 3000
F 0 "U1" H 4600 3300 50  0000 L CNN
F 1 "LM386" H 4600 3200 50  0000 L CNN
F 2 "" H 4650 3100 50  0000 C CNN
F 3 "" H 4750 3200 50  0000 C CNN
	1    4550 3000
	1    0    0    -1  
$EndComp
Wire Wire Line
	4250 3100 4000 3100
Wire Wire Line
	4000 3100 4000 3500
Wire Wire Line
	4000 3500 5100 3500
Wire Wire Line
	5100 3500 5100 3000
Wire Wire Line
	5100 3000 4950 3000
$Comp
L C C1
U 1 1 5A60AC67
P 5250 3000
F 0 "C1" H 5275 3100 50  0000 L CNN
F 1 "47 nF" H 5275 2900 50  0000 L CNN
F 2 "" H 5288 2850 50  0000 C CNN
F 3 "" H 5250 3000 50  0000 C CNN
	1    5250 3000
	0    -1   -1   0   
$EndComp
Wire Wire Line
	5400 3000 6000 3000
Wire Wire Line
	4250 2900 3400 2900
$Comp
L GND #PWR?
U 1 1 5A60AD4D
P 4550 3600
F 0 "#PWR?" H 4550 3350 50  0001 C CNN
F 1 "GND" H 4550 3450 50  0000 C CNN
F 2 "" H 4550 3600 50  0000 C CNN
F 3 "" H 4550 3600 50  0000 C CNN
	1    4550 3600
	1    0    0    -1  
$EndComp
$Comp
L +5V #PWR?
U 1 1 5A60AD75
P 4550 2500
F 0 "#PWR?" H 4550 2350 50  0001 C CNN
F 1 "+5V" H 4550 2640 50  0000 C CNN
F 2 "" H 4550 2500 50  0000 C CNN
F 3 "" H 4550 2500 50  0000 C CNN
	1    4550 2500
	1    0    0    -1  
$EndComp
Wire Wire Line
	4550 2500 4550 2700
Wire Wire Line
	4550 3600 4550 3300
$Comp
L R R1
U 1 1 5A60AE3C
P 3400 2650
F 0 "R1" V 3480 2650 50  0000 C CNN
F 1 "56k" V 3400 2650 50  0000 C CNN
F 2 "" V 3330 2650 50  0000 C CNN
F 3 "" H 3400 2650 50  0000 C CNN
	1    3400 2650
	1    0    0    -1  
$EndComp
$Comp
L R R2
U 1 1 5A60AE91
P 3400 3250
F 0 "R2" V 3480 3250 50  0000 C CNN
F 1 "10k" V 3400 3250 50  0000 C CNN
F 2 "" V 3330 3250 50  0000 C CNN
F 3 "" H 3400 3250 50  0000 C CNN
	1    3400 3250
	1    0    0    -1  
$EndComp
$Comp
L GND #PWR?
U 1 1 5A60B02C
P 3400 3600
F 0 "#PWR?" H 3400 3350 50  0001 C CNN
F 1 "GND" H 3400 3450 50  0000 C CNN
F 2 "" H 3400 3600 50  0000 C CNN
F 3 "" H 3400 3600 50  0000 C CNN
	1    3400 3600
	1    0    0    -1  
$EndComp
Wire Wire Line
	3400 2800 3400 3100
Wire Wire Line
	3400 3400 3400 3600
Connection ~ 3400 2900
Connection ~ 5100 3000
Text Label 5550 3000 0    60   ~ 0
to_speaker
Wire Wire Line
	3400 2500 3400 2350
Wire Wire Line
	3400 2350 2700 2350
Text Label 2750 2350 0    60   ~ 0
pulses
$EndSCHEMATC
