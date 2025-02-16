from functools import partial

import numpy as np


class Covariance:
    def __init__(self, nol: int, alt: np.ma.MaskedArray):
        """assumed covariances

        :param no           number of levels
        :param alt          altitudes
        """

        self.nol = nol
        self.alt = alt

    def gaussian(self, x, mu, sig):
        """Gaussian function

        :param x:   Input value
        :param mu:  Mean value of gaussian
        :param sig: Standard deviation of gaussian
        """
        return np.exp(-((x - mu)*(x - mu))/(2 * sig * sig))

    def traf(self) -> np.ndarray:
        """P (see equation 6)

        Used to transform {ln[H2O], ln[HDO]} state
        into the new coordination systems
        {(ln[H2O]+ln[HDO])/2 and ln[HDO]-ln[H2O]} 
        """
        return np.block([[np.identity(self.nol)*0.5, np.identity(self.nol)*0.5],
                         [-np.identity(self.nol), np.identity(self.nol)]])

    def assumed_covariance(self, species=2, w1=1.0, w2=0.01, correlation_length=2500) -> np.ndarray:
        """Sa' (see equation 7)

        A priori covariance of {(ln[H2O]+ln[HDO])/2 and ln[HDO]-ln[H2O]} state
        Sa See equation 5 in paper

        :param species              Number of atmospheric species (1 or 2)
        :param w1:                  Weight for upper left quadrant
        :param w2:                  Weight for lower right quadrant (ignored with 1 species)
        :param correlation_length:  Assumed correlation of atmospheric levels in meter
        """
        # only 1 or 2 species are allowed
        assert (species >= 1) and (species <= 2)
        result = np.zeros((species * self.nol, species * self.nol))
        for i in range(self.nol):
            for j in range(self.nol):
                # 2500 = correlation length
                # 100% for
                # (ln[H2O]+ln[HDO])/2 state
                result[i, j] = w1 * \
                    self.gaussian(self.alt[i], self.alt[j], correlation_length)
                if species == 2:
                    # 10% for (0.01 covariance)
                    # ln[HDO]-ln[H2O] state
                    result[i + self.nol, j + self.nol] = w2 * \
                        self.gaussian(
                            self.alt[i], self.alt[j], correlation_length)
        return result

    def apriori_covariance(self) -> np.ndarray:
        """Sa (see equation 5)

        A priori Covariance of {ln[H2O], ln[HDO]} state

        Sa' = P * Sa * P.T (equation 7 in paper)
        equals to 
        Sa = inv(P) * Sa' * inv(P.T)
        """
        P = self.traf()
        return np.linalg.inv(P) @ self.apriori_covariance_traf() @ np.linalg.inv(P.T)

    def type1_of(self, matrix) -> np.ndarray:
        """A' (see equation 10)

        Return tranformed martix
        """
        P = self.traf()
        return P @ matrix @ np.linalg.inv(P)

    def c_by_type1(self, A_) -> np.ndarray:
        return np.block([[A_[self.nol:, self.nol:], np.zeros((self.nol, self.nol))],
                         [-A_[self.nol:, :self.nol], np.identity(self.nol)]])

    def c_by_avk(self, avk):
        A_ = self.type1_of(avk)
        return self.c_by_type1(A_)

    def type2_of(self, matrix) -> np.ndarray:
        """A'' (see equation 15)

        A posteriori transformed matrix 
        """
        A_ = self.type1_of(matrix)
        C = self.c_by_type1(A_)
        return C @ A_

    def smoothing_error(self, actual_matrix, to_compare, **kwargs) -> np.ndarray:
        """S's (see equation 11)
        """
        return (actual_matrix - to_compare) @ self.assumed_covariance(**kwargs) @ (actual_matrix - to_compare).T

