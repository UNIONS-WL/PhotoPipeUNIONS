import numpy as np
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.io.fits as fits
import sys
from astropy.wcs import WCS

incat = sys.argv[1]
outcat = sys.argv[2]
image = sys.argv[3]


def sdss_shape_to_sextractor(xx, yy, xy, x, y, wcs):
    """
    Vectorized conversion of LSST base_SdssShape moments to
    approximately equivalent SExtractor A_WORLD, B_WORLD,
    THETA_J2000.

    Parameters
    ----------
    xx, yy, xy : array_like
        base_SdssShape_xx, _yy, _xy [pixel^2]
    x, y : array_like
        Source positions in pixel coordinates.
    wcs : astropy.wcs.WCS
        Celestial WCS.

    Returns
    -------
    A_world, B_world, theta_j2000 : ndarray
        Major/minor RMS axes [deg] and position angle [deg],
        measured east of north.
    """

    xx, yy, xy, x, y = np.broadcast_arrays(
        np.asarray(xx, dtype=float),
        np.asarray(yy, dtype=float),
        np.asarray(xy, dtype=float),
        np.asarray(x, dtype=float),
        np.asarray(y, dtype=float),
    )

    eps = 1e-3  # pixel

    # WCS at source positions
    ra_p_x, dec_p_x = wcs.pixel_to_world_values(x + eps, y)
    ra_m_x, dec_m_x = wcs.pixel_to_world_values(x - eps, y)
    ra_p_y, dec_p_y = wcs.pixel_to_world_values(x, y + eps)
    ra_m_y, dec_m_y = wcs.pixel_to_world_values(x, y - eps)

    _, dec0 = wcs.pixel_to_world_values(x, y)

    # Wrapped RA difference
    def dra(a, b):
        return (a - b + 180.0) % 360.0 - 180.0

    # Local WCS Jacobian:
    #
    # [ dRA/dx   dRA/dy ]
    # [ dDec/dx  dDec/dy ]
    #
    J = np.empty(xx.shape + (2, 2))

    J[..., 0, 0] = dra(ra_p_x, ra_m_x) / (2 * eps)
    J[..., 0, 1] = dra(ra_p_y, ra_m_y) / (2 * eps)
    J[..., 1, 0] = (dec_p_x - dec_m_x) / (2 * eps)
    J[..., 1, 1] = (dec_p_y - dec_m_y) / (2 * eps)

    # Convert RA to physical tangent-plane distance:
    # d(East) = cos(dec) * d(RA)
    J[..., 0, :] *= np.cos(np.deg2rad(dec0))[..., None]

    # Pixel-space moment matrix
    M = np.empty(xx.shape + (2, 2))
    M[..., 0, 0] = xx
    M[..., 0, 1] = xy
    M[..., 1, 0] = xy
    M[..., 1, 1] = yy

    # Transform moments into sky tangent plane:
    #
    # M_sky = J M_pix J^T
    M_sky = J @ M @ np.swapaxes(J, -1, -2)

    # Eigenvalues/eigenvectors of each 2x2 covariance matrix
    eigval, eigvec = np.linalg.eigh(M_sky)

    # eigh returns eigenvalues in ascending order.
    # Last eigenvector is therefore the major axis.
    major = eigval[..., 1]
    minor = eigval[..., 0]

    A_world = np.sqrt(np.maximum(major, 0))
    B_world = np.sqrt(np.maximum(minor, 0))

    # Major-axis eigenvector: [East, North]
    east = eigvec[..., 0, 1]
    north = eigvec[..., 1, 1]

    # Position angle east of north
    theta_j2000 = np.degrees(
        np.arctan2(east, north)
    ) % 180.0

    return A_world, B_world, theta_j2000

wcs = WCS(image)

hdu = fits.open(incat)

data = hdu[1].data
cols = data.columns

A, B, theta = sdss_shape_to_sextractor(
    data["base_SdssShape_xx"],
    data["base_SdssShape_yy"],
    data["base_SdssShape_xy"],
    data["base_SdssShape_x"],
    data["base_SdssShape_y"],
    wcs
)

A = A + 1E-6
B = B + 1E-6

theta = theta - 90.

mag = 2.5*np.log10(data["ext_photometryKron_KronFlux_instFlux"])+27.
magerr = 2.5/data["ext_photometryKron_KronFlux_instFlux"]/np.log(10)*data["ext_photometryKron_KronFlux_instFluxErr"]
flux_radius = np.sqrt(A*B)

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
