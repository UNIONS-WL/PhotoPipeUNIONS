"""Approximate conversion of SDSS adaptive-moment shapes to SExtractor-like quantities.

Caveats: SDSS moments are Gaussian-weighted, SExtractor's are isophotal, and
FLUX_RADIUS is a true enclosed-flux radius. Expect 10-30% differences for
galaxies; the Gaussian factor is only exact for Gaussian profiles.
"""
import numpy as np

FWHM_TO_HALF_LIGHT = np.sqrt(2.0 * np.log(2.0))  # ~1.177: r50 / sigma for a Gaussian


def sdss_to_sextractor(xx, yy, xy, pixel_scale=None, cd=None):
    """Convert SDSS second moments to approximate SExtractor quantities.

    Parameters
    ----------
    xx, yy, xy : float or array
        base_SdssShape_xx, _yy, _xy (pixel^2).
    pixel_scale : float, optional
        Pixel scale in arcsec/pixel. Assumes north-up, east-left, no distortion.
    cd : (2, 2) array-like, optional
        WCS CD matrix in deg/pixel, mapping (dx, dy) -> (xi east, eta north).
        Takes precedence over pixel_scale. Handles rotation and parity.
        (In the LSST stack: wcs.getCdMatrix(pos), in radians -> convert to deg.)

    Returns
    -------
    dict with:
        A_IMAGE, B_IMAGE, THETA_IMAGE (pix, pix, deg from +x toward +y)
        FLUX_RADIUS (pix)
        and, if a WCS/pixel scale is given:
        A_WORLD, B_WORLD (deg), THETA_J2000 (deg, east of north, in (-90, 90]),
        FLUX_RADIUS_ARCSEC
    """
    xx, yy, xy = (np.asarray(v, dtype=float) for v in (xx, yy, xy))

    def principal(sxx, syy, sxy):
        mean = 0.5 * (sxx + syy)
        diff = np.sqrt((0.5 * (sxx - syy)) ** 2 + sxy ** 2)
        a = np.sqrt(np.clip(mean + diff, 0, None))
        b = np.sqrt(np.clip(mean - diff, 0, None))
        return a, b

    def wrap(theta_deg):
        # wrap into (-90, 90]
        return 90.0 - np.mod(90.0 - theta_deg, 180.0)

    a, b = principal(xx, yy, xy)
    theta_img = np.degrees(0.5 * np.arctan2(2.0 * xy, xx - yy))
    flux_radius = FWHM_TO_HALF_LIGHT * np.sqrt(0.5 * (xx + yy))

    out = {
        "A_IMAGE": a,
        "B_IMAGE": b,
        "THETA_IMAGE": theta_img,
        "FLUX_RADIUS": flux_radius,
    }

    if cd is None and pixel_scale is not None:
        s = pixel_scale / 3600.0  # deg/pix
        cd = np.array([[-s, 0.0], [0.0, s]])  # north up, east left

    if cd is not None:
        J = np.asarray(cd, dtype=float)
        # Sigma_sky = J M J^T, with axes (xi = east, eta = north)
        sxx = J[0, 0] ** 2 * xx + 2 * J[0, 0] * J[0, 1] * xy + J[0, 1] ** 2 * yy
        syy = J[1, 0] ** 2 * xx + 2 * J[1, 0] * J[1, 1] * xy + J[1, 1] ** 2 * yy
        sxy = (J[0, 0] * J[1, 0] * xx
               + (J[0, 0] * J[1, 1] + J[0, 1] * J[1, 0]) * xy
               + J[0, 1] * J[1, 1] * yy)
        a_w, b_w = principal(sxx, syy, sxy)
        # Position angle: from north toward east
        theta_j2000 = wrap(np.degrees(0.5 * np.arctan2(2.0 * sxy, syy - sxx)))
        scale_deg = np.sqrt(abs(np.linalg.det(J)))  # mean deg/pix
        out.update({
            "A_WORLD": a_w,
            "B_WORLD": b_w,
            "THETA_J2000": theta_j2000,
            "FLUX_RADIUS_ARCSEC": flux_radius * scale_deg * 3600.0,
        })

    return out


if __name__ == "__main__":
    # Elongated source, 0.2"/pix, north-up east-left
    res = sdss_to_sextractor(xx=4.0, yy=2.0, xy=0.8, pixel_scale=0.2)
    for k, v in res.items():
        print(f"{k:20s} {float(v):.5f}")
