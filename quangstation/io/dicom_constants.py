#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module chứa các hằng số DICOM được sử dụng trong hệ thống.
"""

# SOP Class UIDs
CT_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.2'
MR_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.4'
PET_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.128'
SPECT_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.20'
RT_DOSE_STORAGE = '1.2.840.10008.5.1.4.1.1.481.2'
RT_PLAN_STORAGE = '1.2.840.10008.5.1.4.1.1.481.5'
RT_STRUCTURE_SET_STORAGE = '1.2.840.10008.5.1.4.1.1.481.3'
RT_IMAGE_STORAGE = '1.2.840.10008.5.1.4.1.1.481.1'

# Transfer Syntax UIDs
EXPLICIT_VR_LITTLE_ENDIAN = '1.2.840.10008.1.2.1'
IMPLICIT_VR_LITTLE_ENDIAN = '1.2.840.10008.1.2'
EXPLICIT_VR_BIG_ENDIAN = '1.2.840.10008.1.2.2'

# Modality Values
MODALITY_CT = 'CT'
MODALITY_MR = 'MR'
MODALITY_PT = 'PT'  # PET
MODALITY_NM = 'NM'  # Nuclear Medicine (SPECT)
MODALITY_RTDOSE = 'RTDOSE'
MODALITY_RTPLAN = 'RTPLAN'
MODALITY_RTSTRUCT = 'RTSTRUCT'
MODALITY_RTIMAGE = 'RTIMAGE'

# Common Tags
TAG_PATIENT_ID = '0010,0020'
TAG_PATIENT_NAME = '0010,0010'
TAG_STUDY_INSTANCE_UID = '0020,000D'
TAG_SERIES_INSTANCE_UID = '0020,000E'
TAG_SOP_INSTANCE_UID = '0008,0018'
TAG_MODALITY = '0008,0060'
TAG_SLICE_LOCATION = '0020,1041'
TAG_IMAGE_POSITION_PATIENT = '0020,0032'
TAG_IMAGE_ORIENTATION_PATIENT = '0020,0037'
TAG_PIXEL_SPACING = '0028,0030'
TAG_SLICE_THICKNESS = '0018,0050'

# RT Structure Tags
TAG_ROI_CONTOUR_SEQUENCE = '3006,0039'
TAG_CONTOUR_SEQUENCE = '3006,0040'
TAG_CONTOUR_DATA = '3006,0050'
TAG_ROI_SEQUENCE = '3006,0020'
TAG_ROI_NAME = '3006,0026'
TAG_ROI_NUMBER = '3006,0022'
TAG_ROI_DISPLAY_COLOR = '3006,002A'

# RT Dose Tags
TAG_DOSE_GRID_SCALING = '3004,000E'
TAG_DOSE_UNITS = '3004,0002'
TAG_DOSE_TYPE = '3004,0004'
TAG_DOSE_SUMMATION_TYPE = '3004,000A'

# RT Plan Tags
TAG_FRACTION_GROUP_SEQUENCE = '300A,0070'
TAG_NUMBER_OF_FRACTIONS_PLANNED = '300A,0078'
TAG_BEAM_SEQUENCE = '300A,00B0'
TAG_BEAM_NAME = '300A,00C2'
TAG_BEAM_TYPE = '300A,00C4'
TAG_RADIATION_TYPE = '300A,00C6'
TAG_TREATMENT_MACHINE_NAME = '300A,00B2'
TAG_SOURCE_AXIS_DISTANCE = '300A,00B4'
TAG_BEAM_LIMITING_DEVICE_SEQUENCE = '300A,00B6'
TAG_RT_BEAM_LIMITING_DEVICE_TYPE = '300A,00B8'
TAG_NUMBER_OF_LEAF_JAW_PAIRS = '300A,00BC'
TAG_LEAF_POSITION_BOUNDARIES = '300A,00BE'
TAG_CONTROL_POINT_SEQUENCE = '300A,0111'
TAG_GANTRY_ANGLE = '300A,011E'
TAG_BEAM_LIMITING_DEVICE_ANGLE = '300A,0120'
TAG_PATIENT_SUPPORT_ANGLE = '300A,0122'
TAG_TABLE_TOP_ECCENTRIC_ANGLE = '300A,0125'
TAG_ISOCENTER_POSITION = '300A,012C'
TAG_NOMINAL_BEAM_ENERGY = '300A,0114'
TAG_DOSE_RATE_SET = '300A,0115'
TAG_METERSET_RATE = '300A,035A' 