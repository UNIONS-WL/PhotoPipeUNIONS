import numpy as np
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.io.fits as fits
import sys
from astropy.wcs import WCS
from sdss_to_sextractor import sdss_to_sextractor

incat = sys.argv[1]
outcat = sys.argv[2]
image = sys.argv[3]

wcs = WCS(image)

hdu = fits.open(incat)

data = hdu[1].data
cols = data.columns

xx = data["base_SdssShape_xx"]
xy = data["base_SdssShape_xy"]
yy = data["base_SdssShape_yy"]

# Simple case: north-up, east-left, 0.185768"/pix
res = sdss_to_sextractor(xx, yy, xy, pixel_scale=0.185768)

A = res['A_WORLD']
B = res['B_WORLD']
theta = res['THETA_J2000']
flux_radius = res['FLUX_RADIUS']

# Add 0.25" in quadrature
A = np.sqrt(A**2 + 6.94444e-05**2)
B = np.sqrt(B**2 + 6.94444e-05**2)
flux_radius = np.sqrt(flux_radius**2 + 6.94444e-05**2)

mag = -2.5*np.log10(data["ext_photometryKron_KronFlux_instFlux"])+27.
magerr = 2.5/data["ext_photometryKron_KronFlux_instFlux"]/np.log(10)*data["ext_photometryKron_KronFlux_instFluxErr"]

A_col = fits.Column(name='A_WORLD', format='E', array=A)
B_col = fits.Column(name='B_WORLD', format='E', array=B)
theta_col = fits.Column(name='THETA_J2000', format='E', array=theta)
mag_col = fits.Column(name='MAG_AUTO', format='E', array=mag)
magerr_col = fits.Column(name='MAGERR_AUTO', format='E', array=magerr)
flux_radius_col = fits.Column(name='FLUX_RADIUS', format='E', array=flux_radius)

new_cols = fits.ColDefs((A_col, B_col, theta_col, mag_col, magerr_col, flux_radius_col))

hdu[1] = fits.BinTableHDU.from_columns(cols + new_cols)
hdu[1].name = 'OBJECTS'

hdu.writeto(outcat)
