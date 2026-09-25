import numpy as np
from astropy.io import fits
import sys

fname = sys.argv[1]

hdu = fits.open(fname)

image = hdu[0].data

npix = np.prod(image.shape)

#print(image[0:10,0:10])
#print(np.bitwise_and(image[0:10,0:10],32))

filters = {16:"u", 32:"g", 64:"r", 128:"i", 256:"z", 2048:"z2"}

for bit in (16,32,64,128,256,2048):
    bitmask = np.bitwise_and(image,bit)
    binmask = np.greater(bitmask,0)
    print("%2d %5s %5.1f %2s" % (np.log2(bit), bit, np.sum(binmask)/npix*100, filters[bit]))
