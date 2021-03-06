#!/usr/bin/env python
import os
import sys
import re
import numpy as np
from subprocess import call
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

PI = np.pi
PI2 = 2.0*PI
PI_2 = 0.5*PI
NTH = 30
NPH = 30
TH_SUN = 20.0 # Solar zenith angle in deg
PH_SUN = 110.0 # Solar azimuth angle in deg
IAER = 1 # Rural aerosol model
VIS = 20.0 # Visibility in km
ALBEDO = 0.1 # Surface albedo
WMIN = 300.0 # Min. wavelength in nm
WMAX = 1500.0 # Max. wavelength in nm
BAND_MODEL = 15
DISORT = False
NSTR = 16
MODTRAN_DATDIR = '/usr/local/Mod5.2.0.0/org/DATA'
MODTRAN_BINDIR = '/usr/local/Mod5.2.0.0/org'

def Pol0ToPol(th0,ph0,thi,phi,radians=True): # thi,phi ... measured in the (th0,ph0) coordinate
    if radians:
        th0_r = th0
        ph0_r = ph0
        thi_r = thi
        phi_r = phi
    else:
        th0_r = np.radians(th0)
        ph0_r = np.radians(ph0)
        thi_r = np.radians(thi)
        phi_r = np.radians(phi)
    th0_c = np.cos(th0_r)
    th0_s = np.sin(th0_r)
    ph0_c = np.cos(ph0_r)
    ph0_s = np.sin(ph0_r)
    v_x = np.array([th0_c*ph0_c,th0_c*ph0_s,-th0_s])
    v_y = np.array([-ph0_s,ph0_c,0.0])
    v_z = np.array([th0_s*ph0_c,th0_s*ph0_s,th0_c])
    thi_c = np.cos(thi_r)
    thi_s = np.sin(thi_r)
    phi_c = np.cos(phi_r)
    phi_s = np.sin(phi_r)
    v_i = thi_s*phi_c*v_x+thi_s*phi_s*v_y+thi_c*v_z
    tho = np.arctan2(np.sqrt(v_i[0]*v_i[0]+v_i[1]*v_i[1]),v_i[2])
    pho = np.arctan2(v_i[1],v_i[0])
    if radians:
        return tho,pho
    else:
        return np.degrees(tho),np.degrees(pho)

def run_modtran(th_los=0.0,ph_los=0.0,th_sun=TH_SUN,ph_sun=PH_SUN,iaer=IAER,vis=VIS,albedo=ALBEDO,wmin=WMIN,wmax=WMAX,band_model=BAND_MODEL,disort=DISORT,nstr=NSTR,flux_out=False):
    for fnam in ['modtran.7sc','modtran.flx','modtran.plt','modtran.psc','modtran.tp6','modtran.tp7']:
        if os.path.exists(fnam):
            os.remove(fnam)
    with open('mod5root.in','w') as fp:
        fp.write('modtran\n')
    with open('modtran.tp5','w') as fp:
        fp.write('mmf+2    3    2    1    0    0    0    0    0    0    0    0    1    .000{:>7s}\n'.format(str(albedo)))
        fp.write('{:1s}t {:3d} 0.0380.0000001.000000001.000000000f t f f\n'.format('s' if str(disort)[0].lower()=='s' else 't' if disort else 'f',nstr))
        fp.write('{}_2008\n'.format('p{:0f}'.format(band_model*10) if band_model<1 else '{:02d}'.format(int(band_model+0.1))))
        fp.write('  {:3d}    0    0    0    0    0{:10.5f}.000000000.000000000.000000000.000000000\n'.format(iaer,vis))
        fp.write('    0.0000    0.0000{:10.4f}    0.0000     0.000     0.000    0          0.000\n'.format(th_los))
        fp.write('    2    2   93    0\n')
        fp.write('{:10.4f}{:10.4f}     0.000     0.000     0.000     0.000     0.000     0.000\n'.format(ph_sun-ph_los,th_sun))
        fp.write('{:10.0f}{:10.0f}{:10.3f}{:10.3f}rw        {:10s}\n'.format(1.0e7/wmax,1.0e7/wmin,band_model,band_model*2,' t    f  1' if flux_out else ''))
        fp.write('    0\n')
    if not os.path.exists('DATA'):
        os.symlink(MODTRAN_DATDIR,'DATA')
    call(os.path.join(MODTRAN_BINDIR,'Mod90_5.2.0.0.exe'))

def get_flux():
    with open('modtran.flx','r') as fp:
        while True:
            line = fp.readline()
            if re.search('DIFFUSE',line):
                line = fp.readline()
                break
        lines = fp.read()
    indx = lines.index('=')
    f,fu,fd,fs = np.loadtxt(StringIO(lines[:indx]),usecols=(0,1,2,3),unpack=True)
    fact = f*f
    w = 1.0e7/f[::-1]
    return w,(fu*fact)[::-1],(fd*fact)[::-1],(fs*fact)[::-1]

def get_radiance():
    f,y = np.loadtxt('modtran.plt',unpack=True)
    fact = f*f
    w = 1.0e7/f[::-1]
    return w,(y*fact)[::-1]

th_sun_r = np.radians(TH_SUN)
ph_sun_r = np.radians(PH_SUN)
dth_r = PI/NTH
dph_r = PI2/NPH
tgrd = []
pgrd = []
dgrd = []
for i in range(NTH):
    thi = dth_r*(float(i)+0.5)
    for j in range(NPH):
        phi = dph_r*(float(j)+0.5)
        th_los_r,ph_los_r = Pol0ToPol(th_sun_r,ph_sun_r,thi,phi,radians=True)
        dp = ph_los_r-ph_sun_r
        while dp < -PI:
            dp += PI2
        while dp > PI:
            dp -= PI2
        if th_los_r > PI_2 or dp < 0.0:
            continue
        tgrd.append(th_los_r)
        pgrd.append(ph_los_r)
        dgrd.append(dp)
for th_los_r in [0.0,PI_2]:
    for dp in [0.0,PI_2,PI]:
        ph_los_r = ph_sun_r+dp
        while ph_los_r < -PI:
            ph_los_r += PI2
        while ph_los_r > PI:
            ph_los_r -= PI2
        tgrd.append(th_los_r)
        pgrd.append(ph_los_r)
        dgrd.append(dp)
tgrd = np.array(tgrd)
pgrd = np.array(pgrd)
dgrd = np.array(dgrd)
kmax = tgrd.size
zgrd = []
for k in range(kmax):
    if k==0 or (k+1)%10==0 or k==kmax-1:
        sys.stderr.write('{:4d}/{:4d}\n'.format(k+1,kmax))
    th_los_r = tgrd[k]
    ph_los_r = pgrd[k]
    th_los = np.degrees(th_los_r)
    ph_los = np.degrees(ph_los_r)
    run_modtran(th_los,ph_los)
    wi,yr = get_radiance()
    zgrd.append(yr)
zgrd = np.array(zgrd)

run_modtran(0.0,0.0,flux_out=True)
wf,fu,fd,fs = get_flux()

np.savez('flux.npz',th=tgrd,ph=pgrd,dph=dgrd,radiance=zgrd,wlen=wi,wlen_flux=wf,flux_up=fu,flux_dwn=fd,flux_sun=fs)
