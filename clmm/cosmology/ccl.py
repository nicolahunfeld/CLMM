"""@file ccl.py
Cosmology using CCL
"""
import warnings
import numpy as np

import pyccl as ccl

from .parent_class import CLMMCosmology

from .. utils import _patch_rho_crit_to_cd2018

__all__ = []


class CCLCosmology(CLMMCosmology):
    """
    Cosmology object

    Attributes
    ----------
    backend: str
        Name of back-end used
    be_cosmo: cosmology library
        Cosmology library used in the back-end
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # this tag will be used to check if the cosmology object is accepted by the modeling
        self.backend = 'ccl'

        assert isinstance(self.be_cosmo, ccl.Cosmology)

        # cor factor for sigma_critical
        self.cor_factor = _patch_rho_crit_to_cd2018(
            ccl.physical_constants.RHO_CRITICAL)

    def _init_from_cosmo(self, be_cosmo):

        assert isinstance(be_cosmo, ccl.Cosmology)
        self.be_cosmo = be_cosmo

    def _init_from_params(self, H0, Omega_b0, Omega_dm0, Omega_k0):

        self.be_cosmo = ccl.Cosmology(
            Omega_c=Omega_dm0, Omega_b=Omega_b0, Omega_k=Omega_k0, h=H0/100.0, sigma8=0.8, n_s=0.96,
            T_CMB=2.7255, Neff=3.046, m_nu=[0.06, 0.0, 0.0], transfer_function='eisenstein_hu',
            matter_power_spectrum='linear')

    def _set_param(self, key, value):
        raise NotImplementedError("CCL do not support changing parameters")

    def _get_param(self, key):
        if key == "Omega_m0":
            value = ccl.omega_x(self.be_cosmo, 1.0, "matter")
        elif key == "Omega_b0":
            value = self.be_cosmo['Omega_b']
        elif key == "Omega_dm0":
            value = self.be_cosmo['Omega_c']
        elif key == "Omega_k0":
            value = self.be_cosmo['Omega_k']
        elif key == 'h':
            value = self.be_cosmo['h']
        elif key == 'H0':
            value = self.be_cosmo['h']*100.0
        else:
            raise ValueError(f"Unsupported parameter {key}")
        return value

    def _get_Omega_m(self, z):
        return ccl.omega_x(self.be_cosmo, self.get_a_from_z(z), "matter")

    def _get_E2Omega_m(self, z):
        a = self.get_a_from_z(z)
        return ccl.omega_x(self.be_cosmo, a, "matter")*(ccl.h_over_h0(self.be_cosmo, a))**2

    def _get_rho_m(self, z):
        # total matter density in physical units [Msun/Mpc3]
        a = self.get_a_from_z(z)
        return ccl.rho_x(self.be_cosmo, a, 'matter', is_comoving = False)

    def _eval_da_z1z2(self, z1, z2):
        a1 = self.get_a_from_z(z1)
        a2 = self.get_a_from_z(z2)
        return np.vectorize(ccl.angular_diameter_distance)(self.be_cosmo, a1, a2)

    def _eval_sigma_crit(self, z_len, z_src):
        a_len = self.get_a_from_z(z_len)
        a_src = np.atleast_1d(self.get_a_from_z(z_src))
        cte = ccl.physical_constants.CLIGHT**2 / \
            (4.0*np.pi*ccl.physical_constants.GNEWT *
             ccl.physical_constants.SOLAR_MASS)*ccl.physical_constants.MPC_TO_METER

        z_cut = (a_src < a_len)
        if np.isscalar(a_len):
            a_len = np.repeat(a_len, len(a_src))

        res = np.zeros_like(a_src)

        if np.any(z_cut):
            Ds = ccl.angular_diameter_distance(self.be_cosmo, a_src[z_cut])
            Dl = ccl.angular_diameter_distance(self.be_cosmo, a_len[z_cut])
            Dls = ccl.angular_diameter_distance(
                self.be_cosmo, a_len[z_cut], a_src[z_cut])

            res[z_cut] = (cte*Ds/(Dl*Dls))*self.cor_factor

        res[~z_cut] = np.Inf

        return np.squeeze(res)

    def _eval_linear_matter_powerspectrum(self, k_vals, redshift):
        return ccl.linear_matter_power(
            self.be_cosmo , k_vals, self.get_a_from_z(redshift))
