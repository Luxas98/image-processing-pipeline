# coding: utf8
"""
TODO: Write doc-string
"""
import logging
import numpy as np
import pydicom

from utils import open_file

log = logging.getLogger()


def read(filename):
    with open_file(filename) as fh:
        return pydicom.read_file(fh, force=True)


def float_list(x):
    return [float(y) for y in x]


def extract(dicom_slice):
    image = np.float16(dicom_slice.pixel_array)

    # Convert to Hounsfield units (HU)
    if dicom_slice.RescaleSlope != 1:
        image *= dicom_slice.RescaleSlope

    image += dicom_slice.RescaleIntercept

    metadata = {
        # 'dicom_tags': dicom_slice.dir(),
        'rescale_slope': float(dicom_slice.RescaleSlope),
        'rescale_intercept': float(dicom_slice.RescaleIntercept),
        'space_origin': float_list(dicom_slice.ImagePositionPatient),
        'spacing': float_list(dicom_slice.PixelSpacing),
        'slice_thickness': float(dicom_slice.SliceThickness),
        'patient_position': dicom_slice.PatientPosition,
    }

    return np.int16(image), metadata


def load(filename):
    log.info('Loading dicom slice {}'.format(filename))
    return extract(read(filename))
