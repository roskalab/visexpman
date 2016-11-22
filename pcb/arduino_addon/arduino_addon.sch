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
L CONN_01X08 P3
U 1 1 5833F321
P 900 2800
F 0 "P3" H 900 3250 50  0000 C CNN
F 1 "Digital1" V 1000 2800 50  0000 C CNN
F 2 "" H 900 2800 50  0000 C CNN
F 3 "" H 900 2800 50  0000 C CNN
	1    900  2800
	-1   0    0    1   
$EndComp
$Comp
L CONN_01X10 P4
U 1 1 5833F397
P 900 3900
F 0 "P4" H 900 4450 50  0000 C CNN
F 1 "Digital2" V 1000 3900 50  0000 C CNN
F 2 "" H 900 3900 50  0000 C CNN
F 3 "" H 900 3900 50  0000 C CNN
	1    900  3900
	-1   0    0    1   
$EndComp
$Comp
L CONN_01X06 P1
U 1 1 5833F408
P 900 1000
F 0 "P1" H 900 1350 50  0000 C CNN
F 1 "AnalogIn" V 1000 1000 50  0000 C CNN
F 2 "" H 900 1000 50  0000 C CNN
F 3 "" H 900 1000 50  0000 C CNN
	1    900  1000
	-1   0    0    1   
$EndComp
$Comp
L CONN_01X08 P2
U 1 1 5833F467
P 900 1850
F 0 "P2" H 900 2300 50  0000 C CNN
F 1 "Power" V 1000 1850 50  0000 C CNN
F 2 "" H 900 1850 50  0000 C CNN
F 3 "" H 900 1850 50  0000 C CNN
	1    900  1850
	-1   0    0    1   
$EndComp
Wire Wire Line
	1100 750  1550 750 
Wire Wire Line
	1100 850  1550 850 
Wire Wire Line
	1100 950  1550 950 
Wire Wire Line
	1100 1050 1550 1050
Wire Wire Line
	1100 1150 1550 1150
Wire Wire Line
	1100 1250 1550 1250
Text Label 1400 750  0    60   ~ 0
AD5
Text Label 1550 850  2    60   ~ 0
AD4
Text Label 1550 950  2    60   ~ 0
AD3
Text Label 1550 1050 2    60   ~ 0
AD2
Text Label 1550 1150 2    60   ~ 0
AD1
Text Label 1550 1250 2    60   ~ 0
AD0
Wire Wire Line
	1100 1500 1550 1500
Wire Wire Line
	1100 1600 1550 1600
Wire Wire Line
	1350 1600 1350 1700
Wire Wire Line
	1350 1700 1100 1700
Connection ~ 1350 1600
$Comp
L GND #PWR?
U 1 1 5833FD54
P 1550 1600
F 0 "#PWR?" H 1550 1350 50  0001 C CNN
F 1 "GND" H 1550 1450 50  0000 C CNN
F 2 "" H 1550 1600 50  0000 C CNN
F 3 "" H 1550 1600 50  0000 C CNN
	1    1550 1600
	1    0    0    -1  
$EndComp
Text Label 1550 1500 2    60   ~ 0
Vin
Wire Wire Line
	1100 1800 1700 1800
Wire Wire Line
	1100 1900 1900 1900
$Comp
L +5V #PWR?
U 1 1 5833FDAA
P 1700 1800
F 0 "#PWR?" H 1700 1650 50  0001 C CNN
F 1 "+5V" H 1700 1940 50  0000 C CNN
F 2 "" H 1700 1800 50  0000 C CNN
F 3 "" H 1700 1800 50  0000 C CNN
	1    1700 1800
	1    0    0    -1  
$EndComp
$Comp
L +3.3V #PWR?
U 1 1 5833FDDD
P 1900 1800
F 0 "#PWR?" H 1900 1650 50  0001 C CNN
F 1 "+3.3V" H 1900 1940 50  0000 C CNN
F 2 "" H 1900 1800 50  0000 C CNN
F 3 "" H 1900 1800 50  0000 C CNN
	1    1900 1800
	1    0    0    -1  
$EndComp
Wire Wire Line
	1900 1900 1900 1800
Wire Wire Line
	1100 2000 1550 2000
Text Label 1550 2000 2    60   ~ 0
Reset
Wire Wire Line
	1100 4350 1700 4350
Text Label 1700 4350 2    60   ~ 0
D8
Wire Wire Line
	1100 4250 1700 4250
Text Label 1700 4250 2    60   ~ 0
D9
Wire Wire Line
	1100 4150 1700 4150
Text Label 1700 4150 2    60   ~ 0
D10
Wire Wire Line
	1100 4050 1700 4050
Text Label 1700 4050 2    60   ~ 0
D11
Wire Wire Line
	1100 3150 1700 3150
Text Label 1700 3150 2    60   ~ 0
D0
Wire Wire Line
	1100 3050 1700 3050
Text Label 1700 3050 2    60   ~ 0
D1
Wire Wire Line
	1100 2950 1700 2950
Text Label 1700 2950 2    60   ~ 0
D2
Wire Wire Line
	1100 2850 1700 2850
Text Label 1700 2850 2    60   ~ 0
D3
Wire Wire Line
	1100 2750 1700 2750
Text Label 1700 2750 2    60   ~ 0
D4
Wire Wire Line
	1100 2650 1700 2650
Text Label 1700 2650 2    60   ~ 0
D5
Wire Wire Line
	1100 2550 1700 2550
Text Label 1700 2550 2    60   ~ 0
D6
Wire Wire Line
	1100 2450 1700 2450
Text Label 1700 2450 2    60   ~ 0
D7
Wire Wire Line
	1100 3950 1700 3950
Text Label 1700 3950 2    60   ~ 0
D12
Wire Wire Line
	1100 3850 1700 3850
Text Label 1700 3850 2    60   ~ 0
D13
Wire Wire Line
	1100 3750 1800 3750
$Comp
L GND #PWR?
U 1 1 583403C5
P 1800 3750
F 0 "#PWR?" H 1800 3500 50  0001 C CNN
F 1 "GND" H 1800 3600 50  0000 C CNN
F 2 "" H 1800 3750 50  0000 C CNN
F 3 "" H 1800 3750 50  0000 C CNN
	1    1800 3750
	1    0    0    -1  
$EndComp
$EndSCHEMATC
