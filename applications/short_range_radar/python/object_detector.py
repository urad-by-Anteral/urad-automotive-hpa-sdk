import numpy as np

class ObjectDetecter():

    def __init__(self, max_range_,n_horizontal_zones_):
        self.max_range = max_range_
        self.n_horizontal_zones = n_horizontal_zones_
        self.n_zones = self.max_range * self.n_horizontal_zones

        self.zones_n_hits = np.zeros((self.max_range, self.n_horizontal_zones))
        self.iteration_hit = np.zeros((self.max_range, self.n_horizontal_zones))

    def discretize(self, range, azimuth):
        ind_1 = int(np.floor(self.max_range - range))
        ind_2 = 0
        if 15 < azimuth < 45:
            ind_2 = 4
        elif 45 < azimuth < 75:
            ind_2 = 3
        elif 75 < azimuth < 115:
            ind_2 = 2
        elif 115 < azimuth < 145:
            ind_2 = 1
        else:
            ind_2 = 0
        return ind_1, ind_2

    def update(self, r_points, azimuth_points):
        self.iteration_hit[:, :] = 0
        for r, az in zip(r_points, azimuth_points):
            ind_1, ind_2 = self.discretize(r, az)
            self.iteration_hit[ind_1, ind_2] = 1
        ind_hits = (self.iteration_hit == 1)
        ind_no_hits = (self.iteration_hit == 0)
        self.zones_n_hits[ind_hits] += 1
        self.zones_n_hits[ind_no_hits] = 0

        ind_object_detected = np.argwhere(self.zones_n_hits > 3)
        return ind_object_detected