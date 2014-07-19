#!/usr/bin/env python
from pymoos.MOOSCommClient import MOOSCommClient
from threading import Lock
import sys
from time import sleep
import numpy as np
from bisect import bisect
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from matplotlib.cm import hsv


###################### Settings ################################################
mu_key = 'zEstFriction'
sat_key = 'zAlphaR'
sat_thold = 0.4
mu_max = 0.99
bins = [
    {'max': 0.2,    'desc': 'Ice'},
    {'max': 0.4,    'desc': 'Snow (Hard Packed)'},
    {'max': 0.6,    'desc': 'Earth Road (wet)'},
    {'max': 0.8,    'desc': 'Earth Road (dry)'},
    {'max': mu_max, 'desc': 'Asphalt (dry)'}
]
gui_sleep = 0.2
nbins = len(bins)
################################################################################


class MoosClient(MOOSCommClient):
    """where the data comes in"""

    mu = 0
    sat = False

    def __init__(self):
        self.mu_lock = Lock()
        self.sat_lock = Lock()
        MOOSCommClient.__init__(self)
        self.SetOnConnectCallBack(self._on_connect)
        self.SetOnDisconnectCallBack(self._on_disconnect)
        self.SetOnMailCallBack(self._on_mail)

    def go_baby_go(self):
        self.Run('127.0.0.1', 9000, 'Friction GUI', fundamentalFreq=10)
        for x in range(30):
            if not self.IsConnected():
                sleep(0.1)
                continue
            return
        cfg.logger.error('MoosMiddleware: could not connect to db')
        sys.exit()

    def _on_connect(self):
        self.Register(mu_key)
        self.Register(sat_key)

    def _on_disconnect(self):
        print 'Mu Estimator: MOOS is exiting.'
        sys.exit()

    def _on_mail(self):
        for msg in self.FetchRecentMail():
            key = msg.GetKey()
            if key == mu_key:
                self._set_mu(msg.GetDouble())
            elif  key == sat_key:
                self._set_sat(msg.GetDouble())
            print 'Mu: '+str(self.mu)
            print 'Sat: '+str(self.sat)
            print '\n'

    def _set_mu(self,val):
        with self.mu_lock:
            if val >= mu_max:
                val = mu_max
            self.mu = val

    def _set_sat(self,val):
        with self.sat_lock:
            self.sat = val >= sat_thold

    def get_mu(self):
        with self.mu_lock:
            return self.mu

    def get_sat(self):
        with self.sat_lock:
            return self.sat


class FrictionGUI:
    """This is the GUI"""

    def __init__(self):

        self.moos = MoosClient()

        self.thresholds = [ bin_['max'] for bin_ in bins ]

        plt.ion()
        self.fig, self.ax = plt.subplots()

        self.grid = np.array( [ [.25, y] for y in np.linspace(.2,.8,nbins) ] )
        # go time
        plt.show()
        sleep(1)
        self.moos.go_baby_go()
        self.spin()

    def label(self,xy,text):
        x = xy[0] + .35
        plt.text(x,xy[1],text,ha='center',family='sans-serif',size=14)

    def spin(self):
        while self.moos.IsConnected():
            try:
                self.fig.clf()
                self.ax = self.fig.gca()
                mu = self.moos.get_mu()
                sat = self.moos.get_sat()
                # figure out first bin with max larger than mu
                which_bin = bisect(self.thresholds,mu)
                patches = []
                colors = []
                for bn in range(1,nbins+1):
                    # draw indicator
                    grid = self.grid[bn-1]
                    box = mpatches.FancyBboxPatch(
                        grid - [0.025,0.05], 0.05, 0.1,
                        boxstyle=mpatches.BoxStyle('Round', pad=0.02))
                    patches.append(box)
                    if bn-1 == which_bin:
                        if sat:
                            colors.append(0.30)
                        else:
                            colors.append(1)
                    else:
                        colors.append(0.5)
                    self.label(grid, bins[bn-1]['desc'])
                collection = PatchCollection(patches, cmap=hsv, alpha=1)
                collection.set_clim([0, 1])
                collection.set_array(np.array(colors))
                self.ax.add_collection(collection)
                plt.subplots_adjust(left=0,right=1,bottom=0,top=1)
                plt.axis('equal')
                plt.axis('off')
                plt.show()
                plt.pause(gui_sleep)

            except KeyboardInterrupt:
                print 'GUI Shutting Down'
                sys.exit()
        sys.exit()


def main():
    gui = FrictionGUI()


if __name__ == '__main__':
    main()