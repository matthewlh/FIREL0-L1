import datetime
import itertools
import os
import time

import numpy as np
from spacepy import datamodel as dm

import packet


def dat2time(inval):
    """
    take 8 bytes and change them to a datetime
    """
    if isinstance(inval, str) and len(inval) > 2:
        t0tmp = inval.split(' ')
        t1tmp = [int(v, 16) for v in t0tmp[0:6]]
        t1tmp.append(int(t0tmp[6]+t0tmp[7], 16))
        t0 = datetime.datetime(2000 + t1tmp[0], t1tmp[1], t1tmp[2],
                               t1tmp[3], t1tmp[4], t1tmp[5], 1000*t1tmp[6])
    else:
        try:
            t1tmp = [int(v, 16) for v in inval[0:6]]
        except TypeError:
            t1tmp = inval[0:6]
        try:
            t1tmp.append(int(inval[6]+inval[7], 16))
        except TypeError:
            t1tmp.append(2**8*inval[6] + inval[7])
        try:
            t0 = datetime.datetime(2000 + t1tmp[0], t1tmp[1], t1tmp[2],
                                   t1tmp[3], t1tmp[4], t1tmp[5], 1000*t1tmp[6])
        except ValueError:
            return None
    return t0

class data(object):
    """
    just a few methods common to all the data type classes below
    """
    def write(self, filename, hdf5=False):
        if hdf5:
            dm.toHDF5(filename, self.data)
        else:
            dm.toJSONheadedASCII(filename, self.data, order=['Epoch'] )
        print('    Wrote {0}'.format(os.path.abspath(filename)))
            

class hires(data):
    """
    a hi-res data file
    """
    def __init__(self, inlst):
        dt = zip(*inlst)[0]
        counts = np.hstack(zip(*inlst)[1]).reshape((-1, 12))
        dat = dm.SpaceData()
        dat['Epoch'] = dm.dmarray(dt)
        dat['Epoch'].attrs['CATDESC'] = 'Default Time'
        dat['Epoch'].attrs['FIELDNAM'] = 'Epoch'
        #dat['Epoch'].attrs['FILLVAL'] = datetime.datetime(2100,12,31,23,59,59,999000)
        dat['Epoch'].attrs['LABLAXIS'] = 'Epoch'
        dat['Epoch'].attrs['SCALETYP'] = 'linear'
        dat['Epoch'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['Epoch'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['Epoch'].attrs['VAR_TYPE'] = 'support_data'
        dat['Epoch'].attrs['TIME_BASE'] = '0 AD'
        dat['Epoch'].attrs['MONOTON'] = 'INCREASE'
        dat['Epoch'].attrs['VAR_NOTES'] = 'Epoch at each hi-res measurement'
        dat['hr0'] = dm.dmarray(counts[:,0:6])
        dat['hr0'].attrs['CATDESC'] = 'Detector 0 hi-res'
        dat['hr0'].attrs['ELEMENT_LABELS'] = "hr0-0", "hr0-1", "hr0-2", "hr0-3", "hr0-4", "hr0-5",  
        dat['hr0'].attrs['ELEMENT_NAMES'] =  "hr0-0", "hr0-1", "hr0-2", "hr0-3", "hr0-4", "hr0-5",  
        dat['hr0'].attrs['FILLVAL'] = -1e-31
        dat['hr0'].attrs['LABLAXIS'] = 'Detector 0 hi-res'
        dat['hr0'].attrs['SCALETYP'] = 'log'
        dat['hr0'].attrs['UNITS'] = 'counts'
        dat['hr0'].attrs['VALIDMIN'] = 0
        dat['hr0'].attrs['VALIDMAX'] = 2**16-1
        dat['hr0'].attrs['VAR_TYPE'] = 'data'
        dat['hr0'].attrs['VAR_NOTES'] = 'hr0 for each channel'
        dat['hr0'].attrs['DEPENDNAME_0'] = 'Epoch'
        dat['hr1'] = dm.dmarray(counts[:,6:])
        dat['hr1'].attrs['CATDESC'] = 'Detector 1 hi-res'
        dat['hr1'].attrs['ELEMENT_LABELS'] = "hr1-0", "hr1-1", "hr1-2", "hr1-3", "hr1-4", "hr1-5",  
        dat['hr1'].attrs['ELEMENT_NAMES'] =  "hr1-0", "hr1-1", "hr1-2", "hr1-3", "hr1-4", "hr1-5",  
        dat['hr1'].attrs['FILLVAL'] = -1e-31
        dat['hr1'].attrs['LABLAXIS'] = 'Detector 1 hi-res'
        dat['hr1'].attrs['SCALETYP'] = 'log'
        dat['hr1'].attrs['UNITS'] = 'counts'
        dat['hr1'].attrs['VALIDMIN'] = 0
        dat['hr1'].attrs['VALIDMAX'] = 2**16-1
        dat['hr1'].attrs['VAR_TYPE'] = 'data'
        dat['hr1'].attrs['VAR_NOTES'] = 'hr1 for each channel'
        dat['hr1'].attrs['DEPENDNAME_0'] = 'Epoch'
        self.data = dat

    @classmethod
    def read(self, filename):
        b = packet.BIRDpackets(filename)
        print('    Read {0} packets'.format(len(b)))
        pages = page.fromPackets(b)
        print('    Read {0} pages'.format(len(pages)))
        h = []
        for p in pages:
            h.extend(hiresPage(p))
        # sort the data
        h = sorted(h, key = lambda x: x[0])
        return hires(h)


def printHiresPage(inpage):
    """
    print out a hires page for debugging
    """
    # the first one is 8 bytes then 24
    dat = inpage.split(' ')
    print ' '.join(dat[0:24+8])
    for ii in range(24+8, len(dat), 24+2):
        print ' '.join(dat[ii:ii+24+2])

class hiresPage(list):
    """
    a page of hires data
    """
    def __init__(self, inpage):
        self._datalen = 24
        self._majorTimelen = 8
        self._minorTimelen = 2

        dat = inpage.split(' ')
        dat = [int(v, 16) for v in dat]

        self.t0 = dat2time(inpage[0:25])
        # now the data length is 24
        self.major_data(dat[0:self._datalen+self._majorTimelen])
        start = self._datalen+self._majorTimelen
        for ii in range(start, len(dat), self._datalen+self._minorTimelen): # the index of the start of each FIRE data
            stop = ii+self._datalen+self._minorTimelen  # 24 bytes of data and 2 for a minor time stamp
            self.minor_data(dat[ii:stop])
        # sort the data
        self = sorted(self, key = lambda x: x[0])

    def minor_data(self, inval):
        """
        read in and add minor data to the class
        """
        if len(inval) < self._datalen+self._minorTimelen:
            return
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = self[-1][0]
        us = 1000*(inval[0]*2**8 + inval[1])
        if  us < self[-1][0].microsecond:
            dt += datetime.timedelta(seconds=1)
        if us == 1000000:
            dt += datetime.timedelta(seconds=1)
        elif us > 1000000:
            return
        else:
            dt = dt.replace(microsecond=us)
        d1 = np.asarray(inval[self._minorTimelen::2])
        d2 = np.asarray(inval[self._minorTimelen+1::2])
        self.append([dt, d2*2**8+d1])

    def major_data(self, inval):
        """
        read in and add major data to the class
        """
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = dat2time(inval[0:8])
        d1 = np.asarray(inval[self._majorTimelen::2])
        d2 = np.asarray(inval[self._majorTimelen+1::2])
        self.append([dt, d2*2**8+d1])


class page(str):
    """
    class to represent a page of data for any of the types
    """
    @classmethod
    def fromPackets(self, packets):
        """
        given a BIRDpackets class create a list of pages
        """
        _seqnum = [p.seqnum for p in packets]
        _seqidx = [p.seqidx for p in packets]
        _pktnum = [p.pktnum for p in packets]
        # how many pages are in the file?
        # count through the seqidx and see if it repeats
        npages = 0
        tmp = 0
        pages = []
        pg = ''
        for ii, (si, sn, pn) in enumerate(itertools.izip( _seqnum, _seqidx, _pktnum)):
            if pn == '01' and pg: # start of a new page
                pages.append(pg)
                pg = ''
            elif pn == '01':
                pg = ''
            if pg:
                pg += ' '
            pg += ' '.join(packets[ii].data)
        pages.append(pg)
        return [page(p) for p in pages]



def printConfigPage(inpage):
    """
    print out a hires page for debugging
    """
    # the first one is 8+16 bytes then 16+2
    dat = inpage.split(' ')
    print ' '.join(dat[0:16+8])
    for ii in range(16+8+2, len(dat), 16+2):
        print ' '.join(dat[ii:ii+16+2])

class configPage(list):
    """
    a page of config data
    """
    def __init__(self, inpage):
        self._datalen = 16
        self._majorTimelen = 8
        self._minorTimelen = 2
        dat = inpage.split(' ')
        dat = [int(v, 16) for v in dat]

        self.t0 = dat2time(inpage[0:25])
        # now the data length is 24
        self.major_data(dat[0:self._datalen+ self._majorTimelen])
        start = self._datalen+ self._majorTimelen
        for ii in range(start, len(dat), self._datalen+self._minorTimelen): # the index of the start of each FIRE data
            stop = ii+self._datalen+self._minorTimelen  # 24 bytes of data and 2 for a minor time stamp
            self.minor_data(dat[ii:stop])
        # sort the data
        self = sorted(self, key = lambda x: x[0])

    def minor_data(self, inval):
        """
        read in and add minor data to the class
        """
        if len(inval) < self._datalen+self._minorTimelen+2:
            return
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = self[-1][0] # this is the last time
        second = inval[1]
        minute = inval[0]
        if minute < self[-1][0].minute:
            dt += datetime.timedelta(hours=1)
        dt = dt.replace(minute=minute)
        dt = dt.replace(second=second)
        d1 = np.asarray(inval[self._minorTimelen:]) # 2 bytes of checksum
        self.append([dt, d1])

    def major_data(self, inval):
        """
        read in and add major data to the class
        """
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = dat2time(inval[0:8])
        d1 = np.asarray(inval[ self._majorTimelen:])
        self.append([dt, d1])



class config(data):
    """
    a config data file
    """
    def __init__(self, inlst):
        dt = zip(*inlst)[0]
        data = np.hstack(zip(*inlst)[1]).reshape((-1, 16))
        dat = dm.SpaceData()

        dat['reg00'] = dm.dmarray(data[:,0])
        dat['reg00'].attrs['CATDESC'] = 'Control Register'
        dat['reg00'].attrs['FIELDNAM'] = 'reg{0:02}'.format(0)
        dat['reg00'].attrs['LABLAXIS'] = 'Control Register'
        dat['reg00'].attrs['SCALETYP'] = 'linear'
        #dat['reg00'].attrs['UNITS'] = 'none'
        dat['reg00'].attrs['VALIDMIN'] = 0
        dat['reg00'].attrs['VALIDMAX'] = 2**8-1
        dat['reg00'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg00'].attrs['VAR_NOTES'] = 'Bits: 7-0: 0, 0, uB data on, context on, det2 hi on, det1 hi on, HVPS on, pulser on'
        dat['reg00'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg01'] = dm.dmarray(data[:,1])
        dat['reg01'].attrs['CATDESC'] = 'Hi-Res Interval'
        dat['reg01'].attrs['FIELDNAM'] = 'reg{0:02}'.format(1)
        dat['reg01'].attrs['LABLAXIS'] = 'Hi-Res Interval'
        dat['reg01'].attrs['SCALETYP'] = 'linear'
        #dat['reg01'].attrs['UNITS'] = 'none'
        dat['reg01'].attrs['VALIDMIN'] = 0
        dat['reg01'].attrs['VALIDMAX'] = 2**8-1
        dat['reg01'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg01'].attrs['VAR_NOTES'] = 'Hi-Res Interval'
        dat['reg01'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg02'] = dm.dmarray(data[:,2])
        dat['reg02'].attrs['CATDESC'] = 'Context Bin Selection'
        dat['reg02'].attrs['FIELDNAM'] = 'reg{0:02}'.format(2)
        dat['reg02'].attrs['LABLAXIS'] = 'Context Bin Selection'
        dat['reg02'].attrs['SCALETYP'] = 'linear'
        #dat['reg02'].attrs['UNITS'] = 'none'
        dat['reg02'].attrs['VALIDMIN'] = 0
        dat['reg02'].attrs['VALIDMAX'] = 2**8-1
        dat['reg02'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg02'].attrs['VAR_NOTES'] = 'Context Bin Selection'
        dat['reg02'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg03'] = dm.dmarray(data[:,3])
        dat['reg03'].attrs['CATDESC'] = 'uBurst Bin Selection'
        dat['reg03'].attrs['FIELDNAM'] = 'reg{0:02}'.format(3)
        dat['reg03'].attrs['LABLAXIS'] = 'uBurst Bin Selection'
        dat['reg03'].attrs['SCALETYP'] = 'linear'
        #dat['reg03'].attrs['UNITS'] = 'none'
        dat['reg03'].attrs['VALIDMIN'] = 0
        dat['reg03'].attrs['VALIDMAX'] = 2**8-1
        dat['reg03'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg03'].attrs['VAR_NOTES'] = 'uBurst Bin Selection'
        dat['reg03'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg04'] = dm.dmarray(data[:,4])
        dat['reg04'].attrs['CATDESC'] = 'Detector Max Energy Setpoint'
        dat['reg04'].attrs['FIELDNAM'] = 'reg{0:02}'.format(4)
        dat['reg04'].attrs['LABLAXIS'] = 'Detector Max Energy Setpoint'
        dat['reg04'].attrs['SCALETYP'] = 'linear'
        #dat['reg04'].attrs['UNITS'] = 'none'
        dat['reg04'].attrs['VALIDMIN'] = 0
        dat['reg04'].attrs['VALIDMAX'] = 2**8-1
        dat['reg04'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg04'].attrs['VAR_NOTES'] = 'Detector Max Energy Setpoint'
        dat['reg04'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg05'] = dm.dmarray(data[:,5])
        dat['reg05'].attrs['CATDESC'] = 'Detector Energy Setpoint5'
        dat['reg05'].attrs['FIELDNAM'] = 'reg{0:02}'.format(5)
        dat['reg05'].attrs['LABLAXIS'] = 'Detector Energy Setpoint5'
        dat['reg05'].attrs['SCALETYP'] = 'linear'
        #dat['reg05'].attrs['UNITS'] = 'none'
        dat['reg05'].attrs['VALIDMIN'] = 0
        dat['reg05'].attrs['VALIDMAX'] = 2**8-1
        dat['reg05'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg05'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint5'
        dat['reg05'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg06'] = dm.dmarray(data[:,6])
        dat['reg06'].attrs['CATDESC'] = 'Detector Energy Setpoint4'
        dat['reg06'].attrs['FIELDNAM'] = 'reg{0:02}'.format(6)
        dat['reg06'].attrs['LABLAXIS'] = 'Detector Energy Setpoint4'
        dat['reg06'].attrs['SCALETYP'] = 'linear'
        #dat['reg06'].attrs['UNITS'] = 'none'
        dat['reg06'].attrs['VALIDMIN'] = 0
        dat['reg06'].attrs['VALIDMAX'] = 2**8-1
        dat['reg06'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg06'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint4'
        dat['reg06'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg07'] = dm.dmarray(data[:,7])
        dat['reg07'].attrs['CATDESC'] = 'Detector Energy Setpoint3'
        dat['reg07'].attrs['FIELDNAM'] = 'reg{0:02}'.format(7)
        dat['reg07'].attrs['LABLAXIS'] = 'Detector Energy Setpoint3'
        dat['reg07'].attrs['SCALETYP'] = 'linear'
        #dat['reg07'].attrs['UNITS'] = 'none'
        dat['reg07'].attrs['VALIDMIN'] = 0
        dat['reg07'].attrs['VALIDMAX'] = 2**8-1
        dat['reg07'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg07'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint3'
        dat['reg07'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg08'] = dm.dmarray(data[:,8])
        dat['reg08'].attrs['CATDESC'] = 'Detector Energy Setpoint2'
        dat['reg08'].attrs['FIELDNAM'] = 'reg{0:02}'.format(8)
        dat['reg08'].attrs['LABLAXIS'] = 'Detector Energy Setpoint2'
        dat['reg08'].attrs['SCALETYP'] = 'linear'
        #dat['reg08'].attrs['UNITS'] = 'none'
        dat['reg08'].attrs['VALIDMIN'] = 0
        dat['reg08'].attrs['VALIDMAX'] = 2**8-1
        dat['reg08'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg08'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint2'
        dat['reg08'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg09'] = dm.dmarray(data[:,9])
        dat['reg09'].attrs['CATDESC'] = 'Detector Energy Setpoint1'
        dat['reg09'].attrs['FIELDNAM'] = 'reg{0:02}'.format(9)
        dat['reg09'].attrs['LABLAXIS'] = 'Detector Energy Setpoint1'
        dat['reg09'].attrs['SCALETYP'] = 'linear'
        #dat['reg09'].attrs['UNITS'] = 'none'
        dat['reg09'].attrs['VALIDMIN'] = 0
        dat['reg09'].attrs['VALIDMAX'] = 2**8-1
        dat['reg09'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg09'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint1'
        dat['reg09'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg10'] = dm.dmarray(data[:,10])
        dat['reg10'].attrs['CATDESC'] = 'Detector Energy Setpoint0'
        dat['reg10'].attrs['FIELDNAM'] = 'reg{0:02}'.format(10)
        dat['reg10'].attrs['LABLAXIS'] = 'Detector Energy Setpoint0'
        dat['reg10'].attrs['SCALETYP'] = 'linear'
        #dat['reg10'].attrs['UNITS'] = 'none'
        dat['reg10'].attrs['VALIDMIN'] = 0
        dat['reg10'].attrs['VALIDMAX'] = 2**8-1
        dat['reg10'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg10'].attrs['VAR_NOTES'] = 'Detector Energy Setpoint0'
        dat['reg10'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg11'] = dm.dmarray(data[:,11])
        dat['reg11'].attrs['CATDESC'] = 'Config parameter {0}'.format(11)
        dat['reg11'].attrs['FIELDNAM'] = 'reg{0:02}'.format(11)
        dat['reg11'].attrs['LABLAXIS'] = 'Register {0:02} value'.format(11)
        dat['reg11'].attrs['SCALETYP'] = 'linear'
        #dat['reg11'].attrs['UNITS'] = 'none'
        dat['reg11'].attrs['VALIDMIN'] = 0
        dat['reg11'].attrs['VALIDMAX'] = 2**8-1
        dat['reg11'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg11'].attrs['VAR_NOTES'] = 'register{0:02} data'.format(11)
        dat['reg11'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg12'] = dm.dmarray(data[:,12])
        dat['reg12'].attrs['CATDESC'] = 'Config parameter {0}'.format(12)
        dat['reg12'].attrs['FIELDNAM'] = 'reg{0:02}'.format(12)
        dat['reg12'].attrs['LABLAXIS'] = 'Register {0:02} value'.format(12)
        dat['reg12'].attrs['SCALETYP'] = 'linear'
        #dat['reg12'].attrs['UNITS'] = 'none'
        dat['reg12'].attrs['VALIDMIN'] = 0
        dat['reg12'].attrs['VALIDMAX'] = 2**8-1
        dat['reg12'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg12'].attrs['VAR_NOTES'] = 'register{0:02} data'.format(12)
        dat['reg12'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg13'] = dm.dmarray(data[:,13])
        dat['reg13'].attrs['CATDESC'] = 'Config parameter {0}'.format(13)
        dat['reg13'].attrs['FIELDNAM'] = 'reg{0:02}'.format(13)
        dat['reg13'].attrs['LABLAXIS'] = 'Register {0:02} value'.format(13)
        dat['reg13'].attrs['SCALETYP'] = 'linear'
        #dat['reg13'].attrs['UNITS'] = 'none'
        dat['reg13'].attrs['VALIDMIN'] = 0
        dat['reg13'].attrs['VALIDMAX'] = 2**8-1
        dat['reg13'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg13'].attrs['VAR_NOTES'] = 'register{0:02} data'.format(13)
        dat['reg13'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg14'] = dm.dmarray(data[:,14])
        dat['reg14'].attrs['CATDESC'] = 'Config parameter {0}'.format(14)
        dat['reg14'].attrs['FIELDNAM'] = 'reg{0:02}'.format(14)
        dat['reg14'].attrs['LABLAXIS'] = 'Register {0:02} value'.format(14)
        dat['reg14'].attrs['SCALETYP'] = 'linear'
        #dat['reg14'].attrs['UNITS'] = 'none'
        dat['reg14'].attrs['VALIDMIN'] = 0
        dat['reg14'].attrs['VALIDMAX'] = 2**8-1
        dat['reg14'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg14'].attrs['VAR_NOTES'] = 'register{0:02} data'.format(14)
        dat['reg14'].attrs['DEPEND_0'] = 'Epoch'

        dat['reg15'] = dm.dmarray(data[:,15])
        dat['reg15'].attrs['CATDESC'] = 'Config parameter {0}'.format(15)
        dat['reg15'].attrs['FIELDNAM'] = 'reg{0:02}'.format(15)
        dat['reg15'].attrs['LABLAXIS'] = 'Register {0:02} value'.format(15)
        dat['reg15'].attrs['SCALETYP'] = 'linear'
        #dat['reg15'].attrs['UNITS'] = 'none'
        dat['reg15'].attrs['VALIDMIN'] = 0
        dat['reg15'].attrs['VALIDMAX'] = 2**8-1
        dat['reg15'].attrs['VAR_TYPE'] = 'support_data'
        dat['reg15'].attrs['VAR_NOTES'] = 'register{0:02} data'.format(15)
        dat['reg15'].attrs['DEPEND_0'] = 'Epoch'

        dat['Epoch'] = dm.dmarray(dt)
        dat['Epoch'].attrs['CATDESC'] = 'Default Time'
        dat['Epoch'].attrs['FIELDNAM'] = 'Epoch'
        #dat['Epoch'].attrs['FILLVAL'] = datetime.datetime(2100,12,31,23,59,59,999000)
        dat['Epoch'].attrs['LABLAXIS'] = 'Epoch'
        dat['Epoch'].attrs['SCALETYP'] = 'linear'
        dat['Epoch'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['Epoch'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['Epoch'].attrs['VAR_TYPE'] = 'support_data'
        dat['Epoch'].attrs['TIME_BASE'] = '0 AD'
        dat['Epoch'].attrs['MONOTON'] = 'INCREASE'
        dat['Epoch'].attrs['VAR_NOTES'] = 'Epoch at each configuration point'

        self.data = dat

    @classmethod
    def read(self, filename):
        b = packet.BIRDpackets(filename)
        print('    Read {0} packets'.format(len(b)))
        pages = page.fromPackets(b)
        print('    Read {0} pages'.format(len(pages)))
        h = []
        for p in pages:
            h.extend(configPage(p))
        # sort the data
        h = sorted(h, key = lambda x: x[0])
        return config(h)


def printDatatimesPage(inpage):
    """
    print out a Datatimes page for debugging
    """
    # the first one is 8+8 bytes then 8+8
    dat = inpage.split(' ')
    print ' '.join(dat[0:8+8])
    for ii in range(16+8, len(dat), 16):
        print ' '.join(dat[ii:ii+16])

class datatimesPage(list):
    """
    a page of Datatimes data
    """
    def __init__(self, inpage):
        self._datalen = 8
        self._majorTimelen = 8
        dat = inpage.split(' ')
        dat = [int(v, 16) for v in dat]

        self.t0 = dat2time(inpage[0:25])

        # now the data length is 8
        for ii in range(0, len(dat), self._datalen): # the index of the start of each FIRE data
            stop = ii+self._datalen+self._majorTimelen  # 24 bytes of data and 2 for a minor time stamp
            self.major_data(dat[ii:stop])
        # cull any bad data
        ## this has None in place of data
        self = [v for v in self if None not in v]    
        # sort the data
        self = sorted(self, key = lambda x: x[0])

    def major_data(self, inval):
        """
        read in and add major data to the class
        """
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = dat2time(inval[0:8])
        d1 = dat2time(inval[ self._majorTimelen:])
        self.append([dt, d1])


class datatimes(data):
    """
    a datatimes data file
    """
    def __init__(self, inlst):
        dt = zip(*inlst)[0]
        data = np.hstack(zip(*inlst)[1]).reshape((-1, 1))
        dat = dm.SpaceData()

        dat['time'] = dm.dmarray(data[:,0])
        dat['time'].attrs['CATDESC'] = 'Start or stop time'
        dat['time'].attrs['FIELDNAM'] = 'time'
        dat['time'].attrs['LABLAXIS'] = 'Start or stop time'
        dat['time'].attrs['SCALETYP'] = 'linear'
        #dat['time'].attrs['UNITS'] = 'none'
        dat['time'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['time'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['time'].attrs['VAR_TYPE'] = 'support_data'
        dat['time'].attrs['VAR_NOTES'] = 'Time data started or stopped'
        dat['time'].attrs['DEPEND_0'] = 'Epoch'
        dat['time'].attrs['FILLVAL'] = 'None'

        dat['Epoch'] = dm.dmarray(dt)
        dat['Epoch'].attrs['CATDESC'] = 'Default Time'
        dat['Epoch'].attrs['FIELDNAM'] = 'Epoch'
        #dat['Epoch'].attrs['FILLVAL'] = datetime.datetime(2100,12,31,23,59,59,999000)
        dat['Epoch'].attrs['LABLAXIS'] = 'Epoch'
        dat['Epoch'].attrs['SCALETYP'] = 'linear'
        dat['Epoch'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['Epoch'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['Epoch'].attrs['VAR_TYPE'] = 'support_data'
        dat['Epoch'].attrs['TIME_BASE'] = '0 AD'
        dat['Epoch'].attrs['MONOTON'] = 'INCREASE'
        dat['Epoch'].attrs['VAR_NOTES'] = 'Epoch at each configuration point'

        dat['Mode'] = dm.dmarray(np.zeros(len(dt), dtype=int))
        dat['Mode'][...] = -1
        dat['Mode'].attrs['FIELDNAM'] = 'Mode'
        dat['Mode'].attrs['FILLVAL'] = -1
        dat['Mode'].attrs['LABLAXIS'] = 'FIRE Mode'
        dat['Mode'].attrs['SCALETYP'] = 'linear'
        dat['Mode'].attrs['VALIDMIN'] = 0
        dat['Mode'].attrs['VALIDMAX'] = 1
        dat['Mode'].attrs['VAR_TYPE'] = 'support_data'
        dat['Mode'].attrs['VAR_NOTES'] = 'Is the line FIRE on (=1) or FIRE off (=0)'
        dat['Mode'][::2] = 1
        dat['Mode'][1::2] = 0
        
        self.data = dat

    @classmethod
    def read(self, filename):
        b = packet.BIRDpackets(filename)
        print('    Read {0} packets'.format(len(b)))
        pages = page.fromPackets(b)
        print('    Read {0} pages'.format(len(pages)))
        h = []
        for p in pages:
            h.extend(datatimesPage(p))
        # cull any bad data
        ## this has None in place of data
        h = [v for v in h if None not in v]    
        # sort the data
        h = sorted(h, key = lambda x: x[0])
        return datatimes(h)


def printBurstPage(inpage):
    """
    print out a Burst page for debugging
    """
    # the first one is 8+8 bytes then 8+8
    dat = inpage.split(' ')
    print ' '.join(dat[0:8+10])
    for ii in range(8+10, len(dat), 12):
        print ' '.join(dat[ii:ii+12])

class burstPage(list):
    """
    a page of burst data
    """
    def __init__(self, inpage):
        self._datalen = 10
        self._majorTimelen = 8
        self._minorTimelen = 2
        dat = inpage.split(' ')
        dat = [int(v, 16) for v in dat]

        self.t0 = dat2time(inpage[0:25])
        # now the data length is 24
        self.major_data(dat[0:self._datalen+ self._majorTimelen])
        start = self._datalen+ self._majorTimelen
        for ii in range(start, len(dat), self._datalen+self._minorTimelen): # the index of the start of each FIRE data
            stop = ii+self._datalen+self._minorTimelen  # 24 bytes of data and 2 for a minor time stamp
            self.minor_data(dat[ii:stop])
        # sort the data
        self = sorted(self, key = lambda x: x[0])

    def minor_data(self, inval):
        """
        read in and add minor data to the class
        """
        if len(inval) < self._datalen+self._minorTimelen+2:
            return
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = self[-1][0] # this is the last time
        us = 1000*(inval[0]*2**8 + inval[1])
        if  us < self[-1][0].microsecond:
            dt += datetime.timedelta(seconds=1)
        dt = dt.replace(microsecond=us)
        dt2 = [dt-datetime.timedelta(microseconds=100e3)*i for i in range(9, -1, -1)]
        d1 = np.asarray(inval[self._minorTimelen:]) # 2 bytes of checksum
        d1 = np.asanyarray(['{:02x}'.format(v) for v in d1])
        d2 = [int(v[0], 16) for v in d1]
        d3 = [int(v[1], 16) for v in d1]
        dout = zip(d2, d3)
        for v1, v2 in zip(dt2, dout):
            self.append( (v1, v2) )

    def major_data(self, inval):
        """
        read in and add major data to the class
        """
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = dat2time(inval[0:8])
        # there are 10 times 100ms each before this one
        dt2 = [dt-datetime.timedelta(microseconds=100e3)*i for i in range(9, -1, -1)]
        d1 = np.asarray(inval[ self._majorTimelen:])
        d1 = np.asanyarray(['{:02x}'.format(v) for v in d1])
        d2 = [int(v[0], 16) for v in d1]
        d3 = [int(v[1], 16) for v in d1]
        dout = zip(d2, d3)
        for v1, v2 in zip(dt2, dout):
            self.append( (v1, v2) )


class burst(data):
    """
    a datatimes data file
    """
    def __init__(self, inlst):
        dt = zip(*inlst)[0]
        data = np.hstack(zip(*inlst)[1]).reshape((-1, 2))
        dat = dm.SpaceData()

        dat['Burst'] = dm.dmarray(data[:])
        dat['Burst'].attrs['CATDESC'] = 'Burst parameter'
        dat['Burst'].attrs['FIELDNAM'] = 'Burst'
        dat['Burst'].attrs['LABLAXIS'] = 'Burst Parameter'
        dat['Burst'].attrs['SCALETYP'] = 'linear'
        #dat['time'].attrs['UNITS'] = 'none'
        dat['Burst'].attrs['UNITS'] = ''
        dat['Burst'].attrs['VALIDMIN'] = 0
        dat['Burst'].attrs['VALIDMAX'] = 2**4-1
        dat['Burst'].attrs['VAR_TYPE'] = 'data'
        dat['Burst'].attrs['VAR_NOTES'] = 'Burst parameter compressed onboard'
        dat['Burst'].attrs['DEPEND_0'] = 'Epoch'
        dat['Burst'].attrs['FILLVAL'] = 2**8-1

        dat['Epoch'] = dm.dmarray(dt)
        dat['Epoch'].attrs['CATDESC'] = 'Default Time'
        dat['Epoch'].attrs['FIELDNAM'] = 'Epoch'
        #dat['Epoch'].attrs['FILLVAL'] = datetime.datetime(2100,12,31,23,59,59,999000)
        dat['Epoch'].attrs['LABLAXIS'] = 'Epoch'
        dat['Epoch'].attrs['SCALETYP'] = 'linear'
        dat['Epoch'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['Epoch'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['Epoch'].attrs['VAR_TYPE'] = 'support_data'
        dat['Epoch'].attrs['TIME_BASE'] = '0 AD'
        dat['Epoch'].attrs['MONOTON'] = 'INCREASE'
        dat['Epoch'].attrs['VAR_NOTES'] = 'Epoch at each configuration point'

        self.data = dat

    @classmethod
    def read(self, filename):
        b = packet.BIRDpackets(filename)
        print('    Read {0} packets'.format(len(b)))
        pages = page.fromPackets(b)
        print('    Read {0} pages'.format(len(pages)))
        h = []
        for p in pages:
            h.extend(burstPage(p))
        # sort the data
        h = sorted(h, key = lambda x: x[0])
        return burst(h)


def printContextPage(inpage):
    """
    print out a Context page for debugging
    """
    # the first one is 8+6 bytes then 8+8
    dat = inpage.split(' ')
    print ' '.join(dat[0:8+6])
    for ii in range(8+6, len(dat), 8+6): # all majors in context
        print ' '.join(dat[ii:ii+8+6])

class contextPage(list):
    """
    a page of context data
    """
    def __init__(self, inpage):
        self._datalen = 6
        self._majorTimelen = 8
        self._minorTimelen = 2
        dat = inpage.split(' ')
        dat = [int(v, 16) for v in dat]

        self.t0 = dat2time(inpage[0:25])
        self.major_data(dat[0:self._datalen+self._majorTimelen])
        start = self._datalen+self._majorTimelen
        for ii in range(start, len(dat), self._datalen+self._majorTimelen): # the index of the start of each FIRE data
            stop = ii+self._datalen+self._majorTimelen
            try:
                self.major_data(dat[ii:stop])
            except IndexError: # malformed data for some reason, skip it
                pass
        # drop entries that start with None
        self = [v for v in self if v[0] is not None]
        # sort the data
        self = sorted(self, key = lambda x: x[0])


    def major_data(self, inval):
        """
        read in and add major data to the class
        """
        if (np.asarray(inval) == 0).all(): # is this line fill?
            return
        dt = dat2time(inval[0:8])
        d1 = np.asarray(inval[ self._majorTimelen:])
        d1 = np.asanyarray(['{:02x}'.format(v) for v in d1])
        d2 = int(d1[2] + d1[1] + d1[0], 16)
        d3 = int(d1[5] + d1[4] + d1[3], 16)
        dout = [d2, d3]
#        for v1, v2 in zip(dt, dout):
        self.append( (dt, dout) )


class context(data):
    """
    a context data file
    """
    def __init__(self, inlst):
        dt = zip(*inlst)[0]
        data = np.hstack(zip(*inlst)[1]).reshape((-1, 2))
        dat = dm.SpaceData()

        dat['Context'] = dm.dmarray(data[:])
        dat['Context'].attrs['CATDESC'] = 'Context data'
        dat['Context'].attrs['FIELDNAM'] = 'Context'
        dat['Context'].attrs['LABLAXIS'] = 'Context data'
        dat['Context'].attrs['SCALETYP'] = 'log'
        #dat['time'].attrs['UNITS'] = 'none'
        dat['Context'].attrs['UNITS'] = ''
        dat['Context'].attrs['VALIDMIN'] = 0
        dat['Context'].attrs['VALIDMAX'] = 2**4-1
        dat['Context'].attrs['VAR_TYPE'] = 'data'
        dat['Context'].attrs['VAR_NOTES'] = 'Context data 6s average'
        dat['Context'].attrs['DEPEND_0'] = 'Epoch'
        dat['Context'].attrs['FILLVAL'] = 2**8-1


        dat['Epoch'] = dm.dmarray(dt)
        dat['Epoch'].attrs['CATDESC'] = 'Default Time'
        dat['Epoch'].attrs['FIELDNAM'] = 'Epoch'
        #dat['Epoch'].attrs['FILLVAL'] = datetime.datetime(2100,12,31,23,59,59,999000)
        dat['Epoch'].attrs['LABLAXIS'] = 'Epoch'
        dat['Epoch'].attrs['SCALETYP'] = 'linear'
        dat['Epoch'].attrs['VALIDMIN'] = datetime.datetime(1990,1,1)
        dat['Epoch'].attrs['VALIDMAX'] = datetime.datetime(2029,12,31,23,59,59,999000)
        dat['Epoch'].attrs['VAR_TYPE'] = 'support_data'
        dat['Epoch'].attrs['TIME_BASE'] = '0 AD'
        dat['Epoch'].attrs['MONOTON'] = 'INCREASE'
        dat['Epoch'].attrs['VAR_NOTES'] = 'Epoch at each configuration point'

        self.data = dat

    @classmethod
    def read(self, filename):
        b = packet.BIRDpackets(filename)
        print('    Read {0} packets'.format(len(b)))   
        pages = page.fromPackets(b)
        print('    Read {0} pages'.format(len(pages)))
        h = []
        for p in pages:
            h.extend(contextPage(p))
        # drop entries that start with None
        h = [v for v in h if v[0] is not None]
        # sort the data
        h = sorted(h, key = lambda x: x[0])
        return context(h)


