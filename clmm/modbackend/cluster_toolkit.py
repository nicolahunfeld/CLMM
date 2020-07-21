# Functions to model halo profiles

import cluster_toolkit as ct
import numpy as np
from astropy import units
from ..constants import Constants as const
from .cluster_toolkit_patches import _patch_comoving_coord_cluster_toolkit_rho_m
from . import generic
from . generic import *
import warnings

__all__ = generic.__all__ + ['get_3d_density', 'predict_surface_density', 
           'predict_excess_surface_density', 'angular_diameter_dist_a1a2',
           'get_critical_surface_density', 'predict_tangential_shear',
           'predict_convergence', 'predict_reduced_tangential_shear',
           'predict_magnification']


def get_3d_density(r3d, mdelta, cdelta, z_cl, cosmo, delta_mdef=200, halo_profile_model='nfw'):
    r"""Retrieve the 3d density :math:`\rho(r)`.

    Profiles implemented so far are:

        `nfw`: :math:`\rho(r) = \frac{\rho_0}{\frac{c}{(r/R_{vir})}
        \left(1+\frac{c}{(r/R_{vir})}\right)^2}` [insert citation here]

    Parameters
    ----------
    r3d : array_like, float
        Radial position from the cluster center in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster concentration
    z_cl: float
        Redshift of the cluster
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition; defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:

            `nfw` (default)

    Returns
    -------
    rho : array_like, float
        3-dimensional mass density in units of :math:`h^2\ M_\odot\ pc^{-3}` DOUBLE CHECK THIS

    Notes
    -----
    Need to refactor later so we only require arguments that are necessary for all profiles
    and use another structure to take the arguments necessary for specific models
    """
    cosmo = cclify_astropy_cosmo(cosmo)
    omega_m = cosmo['Omega_c'] + cosmo['Omega_b']
    omega_m_transformed = _patch_comoving_coord_cluster_toolkit_rho_m(omega_m, z_cl)

    if halo_profile_model.lower() == 'nfw':
        rho = ct.density.rho_nfw_at_r(r3d, mdelta, cdelta, omega_m_transformed, delta=delta_mdef)
    else:
        raise ValueError(f"Profile model {halo_profile_model} not currently supported")
    return rho


def predict_surface_density(r_proj, mdelta, cdelta, z_cl, cosmo, delta_mdef=200,
                            halo_profile_model='nfw'):
    r""" Computes the surface mass density

    .. math::
        \Sigma(R) = \Omega_m \rho_{crit} \int^\infty_{-\infty} dz \Xi_{hm} (\sqrt{R^2+z^2}),

    where :math:`\Xi_{hm}` is the halo-matter correlation function.

    Parameters
    ----------
    r_proj : array_like
        Projected radial position from the cluster center in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster concentration
    z_cl: float
        Redshift of the cluster
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition; defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:

            `nfw` (default)

    Returns
    -------
    sigma : array_like, float
        2D projected surface density in units of :math:`h M_\odot\ pc^{-2}`

    Notes
    -----
    Need to refactory so we only require arguments that are necessary for all models and use
    another structure to take the arguments necessary for specific models.
    """
    cosmo = cclify_astropy_cosmo(cosmo)
    omega_m = cosmo['Omega_c'] + cosmo['Omega_b']
    omega_m_transformed = _patch_comoving_coord_cluster_toolkit_rho_m(omega_m, z_cl)

    if halo_profile_model.lower() == 'nfw':
        sigma = ct.deltasigma.Sigma_nfw_at_R(r_proj, mdelta, cdelta, omega_m_transformed,
                                             delta=delta_mdef)
    else:
        raise ValueError(f"Profile model {halo_profile_model} not currently supported")
    return sigma


def predict_excess_surface_density(r_proj, mdelta, cdelta, z_cl, cosmo, delta_mdef=200,
                                   halo_profile_model='nfw'):
    r""" Computes the excess surface density

    .. math::
        \Delta\Sigma(R) = \bar{\Sigma}(<R)-\Sigma(R),

    where

    .. math::
        \bar{\Sigma}(<R) = \frac{2}{R^2} \int^R_0 dR' R' \Sigma(R')

    Parameters
    ----------
    r_proj : array_like
        Projected radial position from the cluster center in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster concentration
    z_cl: float
        Redshift of the cluster
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition; defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:

            `nfw` (default)

    Returns
    -------
    deltasigma : array_like, float
        Excess surface density in units of :math:`h\ M_\odot\ pc^{-2}`.
    """
    cosmo = cclify_astropy_cosmo(cosmo)
    omega_m = cosmo['Omega_c'] + cosmo['Omega_b']
    omega_m_transformed = _patch_comoving_coord_cluster_toolkit_rho_m(omega_m, z_cl)

    if np.min(r_proj)<1.e-11:
        raise ValueError(f"Rmin = {np.min(r_proj):.2e} Mpc/h! This value is too small and may cause computational issues.")

    # Computing sigma on a larger range than the radial range requested, with at least 1000 points.
    sigma_r_proj = np.logspace(np.log10(np.min(r_proj))-1, np.log10(np.max(r_proj))+1, np.max([1000,10*np.array(r_proj).size]))
  
    if halo_profile_model.lower() == 'nfw':
        sigma = ct.deltasigma.Sigma_nfw_at_R(sigma_r_proj, mdelta, cdelta,
                                             omega_m_transformed, delta=delta_mdef)
        # ^ Note: Let's not use this naming convention when transfering ct to ccl....
        deltasigma = ct.deltasigma.DeltaSigma_at_R(r_proj, sigma_r_proj,
                                                   sigma, mdelta, cdelta,
                                                   omega_m_transformed, delta=delta_mdef)
    else:
        raise ValueError(f"Profile model {halo_profile_model} not currently supported")
    return deltasigma


def angular_diameter_dist_a1a2(cosmo, a1, a2=1.):
    r"""This is a function to calculate the angular diameter distance
    between two scale factors because CCL cannot yet do it.

    If only a1 is specified, this function returns the angular diameter
    distance from a=1 to a1. If both a1 and a2 are specified, this function
    returns the angular diameter distance between a1 and a2.

    Temporarily using the astropy implementation.

    Parameters
    ----------
    cosmo : pyccl.core.Cosmology object
            CCL Cosmology object
    a1 : float
        Scale factor.
    a2 : float, optional
        Scale factor.

    Returns
    -------
    d_a : float
        Angular diameter distance in units :math:`M\!pc\ h^{-1}`

    Notes
    -----
    This is definitely broken if other cosmological parameter specifications differ,
    so we'll have to revise this later. We need to switch angular_diameter_distance_z1z2
    to CCL equivalent angular distance once implemented
    """
    redshift1 = _get_z_from_a(a2)
    redshift2 = _get_z_from_a(a1)
    ap_cosmo = astropyify_ccl_cosmo(cosmo)

    # astropy angular diameter distance in Mpc
    # need to return in pc/h
    return ap_cosmo.angular_diameter_distance_z1z2(redshift1, redshift2).to_value(units.pc)\
           * ap_cosmo.H0.value*.01


def get_critical_surface_density(cosmo, z_cluster, z_source):
    r"""Computes the critical surface density

    .. math::
        \Sigma_{crit} = \frac{c^2}{4\pi G} \frac{D_s}{D_LD_{LS}}

    Parameters
    ----------
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    z_cluster : float
        Galaxy cluster redshift
    z_source : array_like, float
        Background source galaxy redshift(s)

    Returns
    -------
    sigma_c : float
        Cosmology-dependent critical surface density in units of :math:`h\ M_\odot\ pc^{-2}`

    Notes
    -----
    We will need :math:`\gamma_\infty` and :math:`\kappa_\infty` for alternative
    z_src_models using :math:`\beta_s`.
    """

    clight_pc_s = const.CLIGHT_KMS.value * 1000. / const.PC_TO_METER.value
    gnewt_pc3_msun_s2 = const.GNEWT.value * const.SOLAR_MASS.value / const.PC_TO_METER.value**3

    aexp_cluster = _get_a_from_z(z_cluster)
    aexp_src = _get_a_from_z(z_source)

    d_l = angular_diameter_dist_a1a2(cosmo, aexp_cluster, 1.0)
    d_s = angular_diameter_dist_a1a2(cosmo, aexp_src, 1.0)
    d_ls = angular_diameter_dist_a1a2(cosmo, aexp_src, aexp_cluster)

    beta_s = np.maximum(0., d_ls/d_s)
    sigma_c = clight_pc_s * clight_pc_s / (4.0 * np.pi * gnewt_pc3_msun_s2) * 1/d_l * np.divide(1., beta_s)
    
    if np.any(np.array(z_source)<=z_cluster):
        warnings.warn(f'Some source redshifts are lower than the cluster redshift. Returning Sigma_crit = np.inf for those galaxies.')
    return sigma_c


def predict_tangential_shear(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo, delta_mdef=200,
                             halo_profile_model='nfw', z_src_model='single_plane'):
    r"""Computes the tangential shear

    .. math::
        \gamma_t = \frac{\Delta\Sigma}{\Sigma_{crit}} = \frac{\bar{\Sigma}-\Sigma}{\Sigma_{crit}}

    or

    .. math::
        \gamma_t = \gamma_\infty \times \beta_s

    Parameters
    ----------
    r_proj : array_like
        The projected radial positions in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster NFW concentration.
    z_cluster : float
        Galaxy cluster redshift
    z_source : array_like, float
        Background source galaxy redshift(s)
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition.  Defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:
        `nfw` (default) - [insert citation here]
    z_src_model : str, optional
        Source redshift model, with the following supported options:
        `single_plane` (default) - all sources at one redshift
        `known_z_src` - known individual source galaxy redshifts e.g. discrete case
        `z_src_distribution` - known source redshift distribution e.g. continuous
        case requiring integration.

    Returns
    -------
    gammat : array_like, float
        tangential shear

    Notes
    -----
    TODO: Implement `known_z_src` and `z_src_distribution` options
    We will need :math:`\gamma_\infty` and :math:`\kappa_\infty` for alternative
    z_src_models using :math:`\beta_s`.
    Need to figure out if we want to raise exceptions rather than errors here?
    """
    delta_sigma = predict_excess_surface_density(r_proj, mdelta, cdelta, z_cluster, cosmo,
                                                 delta_mdef=delta_mdef,
                                                 halo_profile_model=halo_profile_model)
    if z_src_model == 'single_plane':
        sigma_c = get_critical_surface_density(cosmo, z_cluster, z_source)
        gammat = np.nan_to_num(delta_sigma / sigma_c,  nan=np.nan, posinf=np.inf, neginf=-np.inf)
        
    # elif z_src_model == 'known_z_src': # Discrete case
    #     raise NotImplementedError('Need to implemnt Beta_s functionality, or average' +
    #                               'delta_sigma/sigma_c gamma_t = Beta_s*gamma_inf')
    # elif z_src_model == 'z_src_distribution': # Continuous ( from a distribution) case
    #     raise NotImplementedError('Need to implement Beta_s calculation from integrating' +
    #                               'distribution of redshifts in each radial bin')
    else:
        raise ValueError("Unsupported z_src_model")
    
    if np.any(np.array(z_source)<=z_cluster):
        warnings.warn(f'Some source redshifts are lower than the cluster redshift. shear = 0 for those galaxies.')

    return gammat


def predict_convergence(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo, delta_mdef=200,
                        halo_profile_model='nfw', z_src_model='single_plane'):
    r"""Computes the mass convergence

    .. math::
        \kappa = \frac{\Sigma}{\Sigma_{crit}}

    or

    .. math::
        \kappa = \kappa_\infty \times \beta_s

    Parameters
    ----------
    r_proj : array_like
        The projected radial positions in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster NFW concentration.
    z_cluster : float
        Galaxy cluster redshift
    z_source : array_like, float
        Background source galaxy redshift(s)
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition.  Defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:
        `nfw` (default) - [insert citation here]
    z_src_model : str, optional
        Source redshift model, with the following supported options:
        `single_plane` (default) - all sources at one redshift
        `known_z_src` - known individual source galaxy redshifts e.g. discrete case
        `z_src_distribution` - known source redshift distribution e.g. continuous
        case requiring integration.

    Returns
    -------
    kappa : array_like, float
        Mass convergence, kappa.

    Notes
    -----
    Need to figure out if we want to raise exceptions rather than errors here?
    """
    sigma = predict_surface_density(r_proj, mdelta, cdelta, z_cluster, cosmo,
                                    delta_mdef=delta_mdef, halo_profile_model=halo_profile_model)

    if z_src_model == 'single_plane':
        sigma_c = get_critical_surface_density(cosmo, z_cluster, z_source)
        kappa = np.nan_to_num(sigma / sigma_c,  nan=np.nan, posinf=np.inf, neginf=-np.inf)
        
    # elif z_src_model == 'known_z_src': # Discrete case
    #     raise NotImplementedError('Need to implemnt Beta_s functionality, or average' +\
    #                               'sigma/sigma_c kappa_t = Beta_s*kappa_inf')
    # elif z_src_model == 'z_src_distribution': # Continuous ( from a distribution) case
    #     raise NotImplementedError('Need to implement Beta_s calculation from integrating' +\
    #                               'distribution of redshifts in each radial bin')
    else:
        raise ValueError("Unsupported z_src_model")
    
    if np.any(np.array(z_source)<=z_cluster):
        warnings.warn(f'Some source redshifts are lower than the cluster redshift. kappa = 0 for those galaxies.')

    return kappa


def predict_reduced_tangential_shear(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo,
                                     delta_mdef=200, halo_profile_model='nfw',
                                     z_src_model='single_plane'):
    r"""Computes the reduced tangential shear :math:`g_t = \frac{\gamma_t}{1-\kappa}`.

    Parameters
    ----------
    r_proj : array_like
        The projected radial positions in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster NFW concentration.
    z_cluster : float
        Galaxy cluster redshift
    z_source : array_like, float
        Background source galaxy redshift(s)
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition.  Defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:
        `nfw` (default) - [insert citation here]
    z_src_model : str, optional
        Source redshift model, with the following supported options:
        `single_plane` (default) - all sources at one redshift
        `known_z_src` - known individual source galaxy redshifts e.g. discrete case
        `z_src_distribution` - known source redshift distribution, e.g. continuous
        case requiring integration.

    Returns
    -------
    gt : array_like, float
        Reduced tangential shear

    Notes
    -----
    Need to figure out if we want to raise exceptions rather than errors here?
    """
    if z_src_model == 'single_plane':
        kappa = predict_convergence(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo, delta_mdef,
                                    halo_profile_model,
                                    z_src_model)
        gamma_t = predict_tangential_shear(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo,
                                           delta_mdef, halo_profile_model, z_src_model)
        red_tangential_shear = np.nan_to_num(np.divide(gamma_t , (1 - kappa)),  nan=np.nan, posinf=np.inf, neginf=-np.inf)
        
    # elif z_src_model == 'known_z_src': # Discrete case
    #     raise NotImplementedError('Need to implemnt Beta_s functionality, or average' +
    #                               'sigma/sigma_c kappa_t = Beta_s*kappa_inf')
    # elif z_src_model == 'z_src_distribution': # Continuous ( from a distribution) case
    #     raise NotImplementedError('Need to implement Beta_s and Beta_s2 calculation from' +
    #                               'integrating distribution of redshifts in each radial bin')
    else:
        raise ValueError("Unsupported z_src_model")
    
    if np.any(np.array(z_source)<=z_cluster):
        warnings.warn(f'Some source redshifts are lower than the cluster redshift. shear = 0 for those galaxies.')


    return red_tangential_shear


# The magnification is computed taking into account just the tangential shear. This is valid for 
# spherically averaged profiles, e.g., NFW and Einasto (by construction the cross shear is zero).
def predict_magnification(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo, delta_mdef=200,
                        halo_profile_model='nfw', z_src_model='single_plane'):
    r"""Computes the magnification

    .. math::
        \mu = \frac{1}{(1 - \kappa)^2 - |\gamma_t|^2}



    Parameters
    ----------
    r_proj : array_like
        The projected radial positions in :math:`M\!pc\ h^{-1}`.
    mdelta : float
        Galaxy cluster mass in :math:`M_\odot\ h^{-1}`.
    cdelta : float
        Galaxy cluster NFW concentration.
    z_cluster : float
        Galaxy cluster redshift
    z_source : array_like, float
        Background source galaxy redshift(s)
    cosmo : pyccl.core.Cosmology object
        CCL Cosmology object
    delta_mdef : int, optional
        Mass overdensity definition.  Defaults to 200.
    halo_profile_model : str, optional
        Profile model parameterization, with the following supported options:
        `nfw` (default) - [insert citation here]
    z_src_model : str, optional
        Source redshift model, with the following supported options:
        `single_plane` (default) - all sources at one redshift
        `known_z_src` - known individual source galaxy redshifts e.g. discrete case
        `z_src_distribution` - known source redshift distribution e.g. continuous
        case requiring integration.

    Returns
    -------
    mu : array_like, float
        magnification, mu.

    Notes
    -----
    Need to figure out if we want to raise exceptions rather than errors here?
    """
    
    if z_src_model == 'single_plane':
        
        kappa = predict_convergence(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo, delta_mdef,
                                    halo_profile_model,
                                    z_src_model)
    
        gammat = predict_tangential_shear(r_proj, mdelta, cdelta, z_cluster, z_source, cosmo,delta_mdef,
                                    halo_profile_model,
                                    z_src_model)
        
        mu =  1. / ((1-kappa)**2-abs(gammat)**2)
    
    # elif z_src_model == 'known_z_src': # Discrete case
    #     raise NotImplementedError('Need to implemnt Beta_s functionality, or average' +\
    #                               'sigma/sigma_c kappa_t = Beta_s*kappa_inf')
    # elif z_src_model == 'z_src_distribution': # Continuous ( from a distribution) case
    #     raise NotImplementedError('Need to implement Beta_s calculation from integrating' +\
    #                               'distribution of redshifts in each radial bin')
    else:
        raise ValueError("Unsupported z_src_model")
        
    if np.any(np.array(z_source)<=z_cluster):
        warnings.warn(f'Some source redshifts are lower than the cluster redshift. mu = 1 for those galaxies.')

        
    return mu