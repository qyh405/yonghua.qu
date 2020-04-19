# -*- coding: utf-8 -*-
"""
Created on Sun Apr  5 10:56:58 2020
滤光片设置情况
2020年4月11日
2083：650， 850 nm
2084：650， 850 nm
9999：没有测量，路欣在改参数
@author: quyh2_000
"""

import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
from skimage import io
from skimage import util
from skimage import filters
from skimage import transform #rescale, resize, downscale_local_mean
io.use_plugin('pil')

def readRaw(f):
    w = 2560
    h = 1920
    
    img = np.fromfile(f)
def contrast_stretch(im):
    """
    Performs a simple contrast stretch of the given image, from 5-100%.
    """
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 100)
    in_min = np.min(im)
    in_max = np.max(im)

    out_min = 0.0
    out_max = 1.0
    
    k = (out_min - out_max) / (in_min - in_max)
    y1 = out_min
    x1 = in_min
    c = y1 - k * x1 

#    out = im - in_min
#    out *= ((out_min - out_max) / (in_min - in_max))
#    out += in_min
    out = im * k + c

    return out
def extractRedNir(img):
    img =  img.astype('float')
    R = img[:,:,0]
    G = img[:,:,1]
    B = img[:,:,2]

    QE_RED = [0.67411367, 0.09843989, 0.0480523] # Red, Green, Blue QE
    QE_NIR = [0.980176211, 0.89]
    k1 = QE_RED[1]/QE_RED[0]
    k2 = QE_NIR[1]/QE_NIR[0]
    nir = (k1 * R - G) / (k1 - k2)
    scatter = 0.95 #散射比(部分近红外来自外部散射)
    nir = nir * scatter
    red = R - nir #(k2 * R - G) / (k2 - k1)
    red[red < 0] = 0
    
#    red = (r1*k1 + r2*k2)/2
#    red = (red0 + red1)/2
    a = (k1 + k2)/(k1 - k2)
    b = 2/(k1 - k2)
    ndvi = a - b * G/R
    return red, nir, ndvi
def splitRedNir(img, expose, bWorak = False):
    """
    bWorak = True: 用文献Worak, Sensors,2013,13的公式
    """
    
    img =  img.astype('float')
    img = img/np.sqrt(expose)
    
    b = img[:,:,2] # BLUE AS NIR
    
    g = img[:,:,1]
    
    r = img[:,:,0] # RED + DN
    kb = 0.90
    kg = 0.75
    if bWorak:
        DN_nir = (kb*b + kg*g)/2
        DN_red = r - DN_nir
        
    else:
    
        DN_nir = (b + g)/2
        DN_red = ( r / 2)
    return DN_red, DN_nir
def combineRGBNIR(DN_red,DN_nir,k):
    
    
#    nir_f = util.img_as_float32(nir_img)
    
    
    m,n = DN_nir.shape
    x = np.reshape(DN_red,(m*n))
    y = np.reshape(DN_nir,(m*n))
    fig,ax = plt.subplots()
    ax.boxplot([x, y])
    red = k * DN_red 
    ndvi_img = np.divide(DN_nir - red , DN_nir + red)
#    ndvi_img = np.multiply(ndvi_img, DN_nir)#用近红外增强
    
#    ndvi_img = np.divide((b + g - r),r)
    ndvi_img[ndvi_img < 0 ] = 0
    return ndvi_img
def getK(red, nir):
    ndvi =  np.divide(nir -red , nir + red)
    soilNdvi = np.percentile(ndvi,10)
    soil = np.array(ndvi <= soilNdvi)
    r = dn_red[soil]
    n = dn_nir[soil]
    x = r.flatten()
    y = n.flatten()
    #y = np.reshape(DN_nir,(m*n))
    #x = np.reshape(DN_red,(m*n))
    A = np.vstack([x, np.zeros(len(x))]).T
    k,c = np.linalg.lstsq(A, y, rcond=None)[0]
    step = 100
    xx = x[0:-1:step]
    yy = y[0:-1:step]
    fig = plt.figure()
    _ = plt.plot(xx, yy, 'o', label='Original data', markersize=10)
    _ = plt.plot(xx, k*xx + c, 'r', label='Fitted line')
    _ = plt.legend()
    ax = plt.gca()
    ax.set_xlabel('RED')
    ax.set_ylabel('NIR') 
    return k
def calibrateRatio(DN_red,DN_nir):
    
#    fig, ax = plt.subplots()
#    ax.boxplot(N_RED)
    m_NIR = np.mean(DN_nir)
    m_RED = np.mean(DN_red)
    k = m_NIR / m_RED
    m,n = DN_red.shape
    y = np.reshape(DN_nir,(m*n))
    x = np.reshape(DN_red,(m*n))
    A = np.vstack([x, np.ones(len(x))]).T
    
    
    k0,c0 = np.linalg.lstsq(A, y, rcond=None)[0]
    step = 100
    xx = x[0:-1:step]
    yy = y[0:-1:step]
    
    fig = plt.figure()
    _ = plt.plot(xx, yy, 'o', label='Original data', markersize=10)
    _ = plt.plot(xx, k0*xx + c0, 'r', label='Fitted line')
    _ = plt.legend()
    ax = plt.gca()
    ax.set_xlabel('RED')
    ax.set_ylabel('NIR') 
#    ax.set_ylim([0, 50])
#    kk = k
#    RED = (red - c).astype('float')
#    RED[RED < 0] = 0
#    NIR = nir.astype('float')
#    NIR[NIR == 0] = 0.001
#    ndvi = np.divide((NIR - kk*RED),(NIR + kk*RED))
#    ndvi[ndvi == 1] = 0
    return k
    
def plotRAW(f):
    img = np.load(f)
    fig,ax = plt.subplots()
    mx = np.max(img)
    scaledImg = img/mx
    io.imshow(scaledImg)
    outFile = f+'.jpg'
    io.imsave(outFile,img)
    return(scaledImg)
def maskWhiteFromRaw(img):
    r = img[:,:,0]
    g = img[:,:,1]
    b = img[:,:,2]
    thresh = filters.threshold_otsu(r)
    m,n,d = img.shape
    mask = np.zeros((m,n))
    mask[r >=thresh*1.1] = 1
    
    R = np.multiply(r,mask)
    G = np.multiply(g,mask)
    B = np.multiply(b,mask)
    masked = img
    masked[:,:,0] = R
    masked[:,:,1] = G
    masked[:,:,2] = B    
    return(masked)
def getKFromWhite(red,nir):
    red = red[red > 0]
    nir = nir[nir > 0]
    
    red = np.mean(red)
    nir = np.mean(nir)
   
    k = nir / red
    return k, red,nir
    
    
def plotJpeg(f):
    img = io.imread(f)
    fig,ax = plt.subplots()
    io.imshow(img)
def readImage(fn):
    path,ext = os.path.splitext(fn)
    if 'npy' in ext:
        img = np.load(fn)
    else:
        img = io.imread(fn)
    return img
import re
def readAwbGains(paraFile):
    vals = []
    try:
        fobj=open(paraFile,'r')
    except (IOError,e):
        print('Error: Open para file',e)
    else:
        for eachLine in fobj:
            [key,values] = eachLine.split(':')
            if 'awb_gains' == key:
                valList = re.findall(r"\d+\.?\d*",values)
                for v in valList:
                    val = int(v)
                    vals.append(val)
    fobj.close()
    gains = [vals[0]/vals[1], vals[2]/vals[3]]
    return gains
    
def restoreRGB(awbGains, img):
    """
    restore the original RGB value using awb gains value
    """
    r_gain = awbGains[0]
    b_gain = awbGains[1]
    img[:,:,0] = img[:,:,0]/r_gain
    img[:,:,2] = img[:,:,2]/b_gain
    return img
    
                      
#myself = __file__
#fileType = 'jpg'
#imgs = []
#myPath, myFile = os.path.split(myself)
#myPath = os.path.join(myPath,'20200405')
#for root,subpaths,files in os.walk(myPath):
#    for f in files:
#        myName, myExt = os.path.splitext(f)
#        if fileType in myExt and '-1' in myName:
#            rgb_file = f
#        if fileType in myExt and '9999-1_2020_04_05_155500' in myName:
#            nir_file = f
#homeDir = 'H:\\LAIPhotoFTP\\9999\\'
#fWhite = '20832020_04_10_162000.tif'
#fVeg = '20832020_04_10_175000.jpg'
#f = '20832020_04_10_175000.jpg'
#f= '20832020_04_11_115000.jpg'
#f = '20832020_04_11_175000.jpg'

#f = '20842020_04_11_115000.jpg'
#f = '20842020_04_11_121500.jpg'
#homeDir = 'H:\\LAIPhotoFTP\\20200415\\新建文件夹 (2)\\'
#f = '9999-2_2020_04_15_090600-veg.jpeg'
#fPaper = '9999-2_2020_04_15_085800-white_small.tif'
#
#
#homeDir = 'H:\\LAIPhotoFTP\\20200415\\pm\\相机'
#
#
#
#
#homeDir = 'H:\\LAIPhotoFTP\\20200415\\pm2\\'
#fWhite = '9999-2_2020_04_15_151200.npy'
#fVeg = '9999-2_2020_04_15_151600.npy'

    
    
    
#homeDir = 'H:\LAIPhotoFTP\\9999'
#
homeDir = 'd:\\test\\20200418\\'
#fVeg = 'Composite (RGB)_2020_04_18_1700.jpg'
#fWhite = 'Composite (RGB)_2020_04_18_1700.jpg'
fVeg = '9999_2_2020_04_18_172000.npy'
fWhite = fVeg
fPara = '9999_2_2020_04_18_172000.txt'

whiteFile = os.path.join(homeDir,fWhite)
vegFile = os.path.join(homeDir, fVeg)
paraFile = os.path.join(homeDir,fPara)

awbGains = readAwbGains(paraFile)

whiteImage = readImage(whiteFile)
whiteImage = restoreRGB(awbGains,whiteImage)
white = maskWhiteFromRaw(whiteImage)
expose = 1
#redRef,nirRef = splitRedNir(white, expose, bWorak = True)
redRef,nirRef = extractRedNir(white)

k,redMean,nirMean = getKFromWhite(redRef,nirRef)

print('k = {}'.format(k))

img = readImage(vegFile)
img = restoreRGB(awbGains,img)
expose = 1#1/269
dn_red,dn_nir = extractRedNir(img)
#dn_red,dn_nir = splitRedNir(img, expose,bWorak = True)
Rred = dn_red/redMean
Rnir = dn_nir/nirMean
k = 1.2
ndviDN = combineRGBNIR(dn_red,dn_nir,k)
ndviR = combineRGBNIR(Rred,Rnir,k)

ndvi_enhanced = contrast_stretch(ndviDN)
rows = 1
cols = 2
fig,axes  = plt.subplots(rows,cols,figsize = (12,6))
ax = plt.subplot(rows,cols,1)
ax.imshow(img)
ax = plt.gca()
ax.set_title('Red-Nir Image')

ax = plt.subplot(rows,cols,2)
ax.set_title('NDVI')
cmap0 = ['rainbow', 'gist_rainbow', 'PuBuGn', 'YlGn','gist_heat','YlOrBr','OrRd']
cmap1 = ['nipy_spectral', 'twilight_shifted_r','RdYlGn']
cmap = []
cmap.append(cmap0)
cmap.extend(cmap1)
i = 1
cm = cmap[i]
im = ax.imshow(ndviDN,cmap = cm)


#ax = plt.subplot(1,3,3)
#ax.set_title('NDVI_R')
#im = io.imshow(ndvi_enhanced, cmap = 'viridis')


#img = plotRAW(f)



