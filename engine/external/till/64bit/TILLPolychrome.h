// TILLPolychrome.h
//
// Copyright 2005-2006 Bruxton Corporation.

// This file defines the API interface for controlling the
// TILL Polychrome V.

#ifndef TILLPolychrome_H
#define TILLPolychrome_H

#include <windows.h>

#ifdef __cplusplus
extern "C" {
#endif

int WINAPI TILLPolychrome_OpenPort(void** handle, const char* port);
int WINAPI TILLPolychrome_Open(void** handle, int index);

void WINAPI TILLPolychrome_Close(void* handle);
int WINAPI TILLPolychrome_Stop(void* handle);

void WINAPI TILLPolychrome_GetStatusText(void* handle, int status, char* text, int size);

int WINAPI TILLPolychrome_GetConfiguration(
	void* handle,
	char* model,
	int model_size,
	char* identification,
	int identification_size,
	bool* motorized_intensity_control,
	bool* motorized_bandwidth_control);

int WINAPI TILLPolychrome_GetFeatures(
	void* handle,
	int* command_set,
	bool* motorized_intensity_control,
	bool* motorized_bandwidth_control);

int WINAPI TILLPolychrome_GetBandwidthRange(
	void* handle,
	double* minimum,
	double* maximum,
	double* startup);

int WINAPI TILLPolychrome_GetIntensityRange(
	void* handle,
	bool* motorized_control,
	double* minimum,
	double* maximum);

int WINAPI TILLPolychrome_GetIntervalResolution(void* handle, double* resolution);

int WINAPI TILLPolychrome_GetWavelengthRange(void* handle, double* resolution, double* minimum, double* maximum);

int WINAPI TILLPolychrome_GetWavelengthVoltage(void* handle, double wavelength, double* voltage);

int WINAPI TILLPolychrome_Delay(void* handle, double duration);

int WINAPI TILLPolychrome_GetStatus(void* handle, bool* busy, int* mark);

int WINAPI TILLPolychrome_SetAnalogInput(void* handle);

int WINAPI TILLPolychrome_SetBandwidth(void* handle, double bandwidth, double intensity);

int WINAPI TILLPolychrome_SetRestingWavelength(void* handle, double wavelength);

int WINAPI TILLPolychrome_SetTriggerIn(void* handle, bool active_high);

int WINAPI TILLPolychrome_SetTriggerOut(void* handle, bool active_high, int pulse_width);

int WINAPI TILLPolychrome_SetWavelength(
	void* handle,
	double wavelength,
	double duration,
	bool return_to_resting_wavelength);

int WINAPI TILLPolychrome_SetWavelengthIncrement(
	void* handle,
	double wavelength_base,
	double wavelength_increment);

int WINAPI TILLPolychrome_SetWavelengthTriggerIn(
	void* handle,
	double wavelength,
	bool start_trigger_enable,
	double start_delay_duration,
	bool illumination_trigger_enable,
	double illumination_duration,
	bool trigger_as_gate,
	bool return_to_resting_wavelength,
	bool repeat);

int WINAPI TILLPolychrome_SetWavelengthTriggerOut(
	void* handle,
	double wavelength,
	double start_delay_duration,
	bool start_pretrigger_enable,
	double start_pretrigger_time,
	double illumination_duration,
	bool illumination_pretrigger_enable,
	double illumination_pretrigger_time,
	bool return_to_resting_wavelength,
	bool repeat);

int WINAPI TILLPolychrome_WaitTriggerIn(void* handle, bool trigger_as_gate);

int WINAPI TILLPolychrome_ProtocolBegin(void* handle);
int WINAPI TILLPolychrome_ProtocolEnd(void* handle);
int WINAPI TILLPolychrome_ProtocolBeginLoop(void* handle, int count);
int WINAPI TILLPolychrome_ProtocolEndLoop(void* handle);
int WINAPI TILLPolychrome_ProtocolMark(void* handle, int mark);

typedef struct TILLPolychrome_Configuration_t
{
	// Presentation section
	char model[48];
	char identification[16];

	// Identification section
	int serial_number;
	int device_type;
	int device_version;
	int OEM_version;

	// Construction section
	int hardware_version;
	int firmware_version;
	int command_set;
	int power_source;

	// Capabilities section
	bool exit_slit_motorized;
	int exit_slit_offset;
	bool entrance_slit_motorized;
	int entrance_slit_offset;
	double bandwidth_minimum;
	double bandwidth_maximum;

	// Settings section
	double wavelength_resting;
	double bandwidth_startup;
	bool autocalibration_enabled;

	// Filter section
	double triple_band_filter_1;
	double triple_band_filter_2;
	double triple_band_filter_3;

	// Calibration section
	int calibration_amplitude;
	int calibration_offset;
} TILLPolychrome_Configuration_t;

int WINAPI TILLPolychrome_ServiceOpen(void** handle, int index, int baud_rate);

int WINAPI TILLPolychrome_ServiceOpenPort(
	void** handle,
	const char* port,
	int baud_rate);

int WINAPI TILLPolychrome_ServiceCalibrate(void* handle);

int WINAPI TILLPolychrome_ServiceGetConfiguration(
	void* handle,
	TILLPolychrome_Configuration_t* configuration);

int WINAPI TILLPolychrome_ServiceSetConfiguration(
	void* handle,
	const TILLPolychrome_Configuration_t* configuration);

int WINAPI TILLPolychrome_ServiceWriteConfiguration(
	void* handle,
	const void* configuration,
	int configuration_length);

int WINAPI TILLPolychrome_ServiceGetInformation(
	void* handle,
	int information_type,
	void* data,
	int data_length,
	int* information_length);

int WINAPI TILLPolychrome_ServiceEnableGalvanometer(void* handle);

int WINAPI TILLPolychrome_ServiceDisableGalvanometer(void* handle);

int WINAPI TILLPolychrome_ServiceGetAnalogInput(void* handle, double* voltage);

int WINAPI TILLPolychrome_ServiceSendCommand(
	void* handle,
	int command_code,
	const char* parameters,
	int parameters_length,
	char* response,
	int response_size,
	int* response_length);

#ifdef __cplusplus
}
#endif

#endif
