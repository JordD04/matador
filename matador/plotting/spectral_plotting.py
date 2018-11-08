# coding: utf-8
# Distributed under the terms of the MIT License.

""" This submodule contains functions to plot densities of states and
bandstructures for electronic and vibrational calculations.

"""


import os
import numpy as np
from matador.utils.viz_utils import get_element_colours
from matador.plotting.plotting import plotting_function


@plotting_function
def plot_spectral(seeds, **kwargs):
    """ This function wraps all of the spectral plotting capability of matador.
    When provided with a seed, or seeds, several files will be checked:

        - <seed>.bands: CASTEP bandstructure expected, not DOS,
        - <seed>.adaptive.dat: OptaDOS total DOS,
        - <seed>.pdos.dat: OptaDOS pDOS,
        - <seed>.pdis.dat: OptaDOS projected dispersion,

    or, if the "phonons" flag is passed, or if a <seed>.phonon file is detected,

        - <seed>.phonon: CASTEP phonon dispersion curves expected,
        - <seed>.phonon_dos: CASTEP phonon DOS.

    This function will then automatically choose what to plot, favouring a bandstructure
    with "the-most-projected" DOS it can find.

    Parameters:
        seeds (list): list of filenames of bands/phonon files

    Keyword Arguments:
        plot_bandstructure (bool): whether to plot bandstructure, if available
        plot_dos (bool): whether to plot density of states, if available
        plot_pdis (bool): whether to plot projected dispersion, if available
        dos (str): separate seed name for pDOS/DOS data
        phonons (bool): whether to plot phonon or electronic data
        labels (list): list of strings for legend labels for multiple bandstructures
        gap (bool): whether to draw on the band gap
        colour_by_seed (bool): plot with a separate colour per bandstructure
        external_efermi (float): replace scraped Fermi energy with this value (eV)
        highlight_bands (list): list of integer indices, colour the bands with these indices in red
        band_colour (str): if passed "occ", bands will be coloured using cmap depending on whether
            they lie above or below the Fermi level. If passed 'random', colour bands randomly from
            the cmap. Otherwise, override all colour options with matplotlib-interpretable colour
            (e.g. hexcode or html colour name) to use for all bands (DEFAULT: 'occ').
        cmap (str): matplotlib colourmap name to use for the bands
        n_colours (int): number of colours to use from cmap (DEFAULT: 4).
        no_stacked_pdos (bool): whether to plot projected DOS as stack or overlapping.
        spin_only (str): either 'up' or 'down' to only plot one spin channel.
        preserve_kspace_distance (bool): whether to preserve distances in reciprocal space when
            linearising the kpoint path. If False, bandstructures of different lattice parameters
            with the same Bravais lattice can be more easily compared. If True, bandstructures may
            appear rarefied or compressed in particular regions.
        band_reorder (bool): try to reorder bands based on local gradients (DEFAULT: True for phonons, otherwise False).
        title (str): optional plot title
        pdos_hide_tot (bool): whether or not to plot the total DOS on a PDOS plot; this is to hide
            regions where the PDOS is negative (leading to total DOS lower than stacked PDOS) (DEFAULT: False).

    """
    import matplotlib.pyplot as plt
    from cycler import cycler
    # set defaults and update class with desired values
    prop_defaults = {'plot_bandstructure': True, 'plot_dos': True, 'plot_pdis': True,
                     'phonons': False, 'gap': False,
                     'colour_by_seed': False, 'external_efermi': None,
                     'labels': None, 'cmap': None, 'band_colour': 'occ',
                     'n_colours': 4, 'spin_only': None, 'figsize': None,
                     'no_stacked_pdos': False, 'preserve_kspace_distance': False,
                     'band_reorder': None, 'title': None,
                     'verbosity': 0, 'highlight_bands': None, 'pdos_hide_tot': True}
    prop_defaults.update(kwargs)
    kwargs = prop_defaults

    if kwargs.get('cmap') is None:
        kwargs['colours'] = list(plt.rcParams['axes.prop_cycle'].by_key()['color'])
        plt.rcParams['axes.prop_cycle'] = cycler('color', kwargs['colours'])
    else:
        if isinstance(kwargs['cmap'], str):
            print('Adjusting colour palette... to {}'.format(kwargs.get('cmap')))
            kwargs['colours'] = plt.cm.get_cmap(kwargs.get('cmap')).colors
            plt.rcParams['axes.prop_cycle'] = cycler('color', kwargs['colours'])
        elif isinstance(kwargs['cmap'], list):
            print('Reading list of colours {}...'.format(kwargs.get('cmap')))
            kwargs['colours'] = kwargs['cmap']
            plt.rcParams['axes.prop_cycle'] = cycler('color', kwargs['colours'])

    if (kwargs.get('phonons') and kwargs['band_colour'] == 'occ') or kwargs['band_colour'] == 'random':
        kwargs['band_colour'] = None

    if not isinstance(seeds, list):
        seeds = [seeds]

    if kwargs.get('plot_window') is not None:
        if isinstance(kwargs.get('plot_window'), list):
            if len(kwargs.get('plot_window')) != 2:
                exit('plot_window must have length 2 or be a single number')
            kwargs['plot_window'] = sorted(kwargs.get('plot_window'))
        else:
            kwargs['plot_window'] = (-kwargs.get('plot_window'), kwargs.get('plot_window'))
    else:
        kwargs['plot_window'] = None

    if kwargs['plot_dos']:
        # check an optados file exists
        exts = ['pdos.dat', 'adaptive.dat', 'fixed.dat', 'linear.dat', 'jdos.dat', 'phonon_dos', 'bands_dos']
        kwargs['plot_dos'] = any([any([os.path.isfile('{}.{}'.format(seed, ext)) for ext in exts]) for seed in seeds])

    figsize = kwargs['figsize']
    if kwargs['plot_bandstructure'] and not kwargs['plot_dos']:
        if figsize is None:
            figsize = (7, 6)
        fig, ax_dispersion = plt.subplots(figsize=figsize)
    elif kwargs['plot_bandstructure'] and kwargs['plot_dos']:
        if figsize is None:
            figsize = (8, 6)
        fig, ax_grid = plt.subplots(1, 3, figsize=figsize, sharey=True,
                                    gridspec_kw={'width_ratios': [4, 1, 1],
                                                 'wspace': 0.05,
                                                 'left': 0.15})
        ax_dispersion = ax_grid[0]
        ax_dos = ax_grid[1]
        ax_grid[2].axis('off')
    elif not kwargs['plot_bandstructure'] and kwargs['plot_dos']:
        if figsize is None:
            figsize = (6, 3)
        fig, ax_dos = plt.subplots(1, figsize=figsize)

    kwargs['valence'] = kwargs['colours'][0]
    kwargs['conduction'] = kwargs['colours'][-1]
    kwargs['crossing'] = kwargs['colours'][int(len(kwargs['colours']) / 2)]

    if len(seeds) > 1 or kwargs.get('colour_by_seed'):
        kwargs['seed_colours'] = kwargs['colours']
        kwargs['ls'] = ['-'] * len(seeds)
        kwargs['colour_by_seed'] = True
        if kwargs.get('labels') is None:
            kwargs['labels'] = [seed.split('/')[-1].split('.')[0] for seed in seeds]
    else:
        kwargs['ls'] = []
        kwargs['colour_by_seed'] = False
        for i in range(len(seeds)):
            if i % 3 == 0:
                kwargs['ls'].append('-')
            elif i % 3 == 1:
                kwargs['ls'].append('--')
            elif i % 3 == 2:
                kwargs['ls'].append('-.')

    bbox_extra_artists = []
    if kwargs['plot_bandstructure']:
        ax_dispersion = dispersion_plot(seeds, ax_dispersion, kwargs, bbox_extra_artists)

    if kwargs['plot_dos']:
        ax_dos = dos_plot(seeds, ax_dos, kwargs, bbox_extra_artists)

    if kwargs.get('title') is not None:
        fig.suptitle(kwargs.get('title'))

    if any([kwargs.get('pdf'), kwargs.get('svg'), kwargs.get('png')]):
        if not bbox_extra_artists:
            bbox_extra_artists = None
        filename = seeds[0].split('/')[-1].replace('.bands', '').replace('.phonon', '') + '_spectral'
        if kwargs.get('pdf'):
            plt.savefig('{}.pdf'.format(filename),
                        bbox_inches='tight', transparent=True, bbox_extra_artists=bbox_extra_artists)
        if kwargs.get('svg'):
            plt.savefig('{}.svg'.format(filename),
                        bbox_inches='tight', transparent=True, bbox_extra_artists=bbox_extra_artists)
        if kwargs.get('png'):
            plt.savefig('{}.png'.format(filename),
                        bbox_inches='tight', transparent=True, bbox_extra_artists=bbox_extra_artists)

    else:
        plt.tight_layout()
        print('Displaying plot...')
        plt.show()


def dispersion_plot(seeds, ax_dispersion, kwargs, bbox_extra_artists):
    """ Plot a dispersion/bandstructure on the given axis. Will detect
    and projected dispersion data automatically.

    Parameters:
        seeds (list): the seednames of the data to plot.
        ax_dispersion (matplotlib.Axes): the axis to plot on.
        kwargs (dict): any plotting keywords (from e.g. dispersion script).
        bbox_extra_artists (list): a list to which to append legends.

    Returns:
        matplotlib.Axes: the axis that was plotted on.

    """
    from matador.scrapers.castep_scrapers import bands2dict, phonon2dict
    from cycler import cycler
    import matplotlib.pyplot as plt
    plotted_pdis = False
    for seed_ind, seed in enumerate(seeds):
        seed = seed.replace('.bands', '').replace('.phonon', '')
        if os.path.isfile('{}.phonon'.format(seed)):
            dispersion, s = phonon2dict(seed + '.phonon', verbosity=kwargs.get('verbosity'))
            if not s:
                raise RuntimeError(dispersion)
            branch_key = 'qpoint_branches'
            num_key = 'num_qpoints'
            path_key = 'qpoint_path'
            eig_key = 'eigenvalues_q'
            band_key = 'num_branches'
            dispersion['num_spins'] = 1
            spin_key = 'num_spins'
            if kwargs['plot_window'] is None:
                kwargs['plot_window'] = [min(-10, np.min(dispersion[eig_key])-10), np.max(dispersion[eig_key])]

            path = _linearise_path(dispersion, path_key, branch_key, num_key, kwargs)

        elif os.path.isfile('{}.bands'.format(seed)):
            dispersion, s = bands2dict(seed + '.bands',
                                       summary=True,
                                       gap=kwargs.get('gap'),
                                       external_efermi=kwargs.get('external_efermi'),
                                       verbosity=kwargs.get('verbosity'))
            if not s:
                raise RuntimeError(dispersion)
            branch_key = 'kpoint_branches'
            num_key = 'num_kpoints'
            path_key = 'kpoint_path'
            eig_key = 'eigenvalues_k_s'
            band_key = 'num_bands'
            spin_key = 'num_spins'

            if kwargs['plot_window'] is None:
                kwargs['plot_window'] = [-10, 10]

            path = _linearise_path(dispersion, path_key, branch_key, num_key, kwargs)

            if os.path.isfile('{}.pdis.dat'.format(seed)) and len(seeds) == 1 and kwargs['plot_pdis']:
                ax_dispersion = projected_bandstructure_plot(seed, ax_dispersion, path, dispersion, bbox_extra_artists)
                kwargs['band_colour'] = 'grey'
                plotted_pdis = True

        else:
            raise RuntimeError('{}.bands/.phonon not found.'.format(seed))

        if kwargs['band_reorder'] or (kwargs['band_reorder'] is None and kwargs['phonons']):
            print('Reordering bands based on local gradients...')
            dispersion[eig_key] = match_bands(dispersion[eig_key], dispersion[branch_key])

        # loop over branches and plot
        if not plotted_pdis:
            for branch_ind, branch in enumerate(dispersion[branch_key]):
                # seem to have to reset colours here for some reason
                plt.rcParams['axes.prop_cycle'] = cycler('color', kwargs['colours'])
                for ns in range(dispersion[spin_key]):
                    if ns == 1 and kwargs.get('spin_only') == 'up':
                        continue
                    elif ns == 0 and kwargs.get('spin_only') == 'down':
                        continue
                    for nb in range(dispersion[band_key]):
                        colour, alpha, label = _get_lineprops(dispersion, eig_key, spin_key, nb, ns, branch, branch_ind, seed_ind, kwargs)

                        ax_dispersion.plot(path[(np.asarray(branch)-branch_ind).tolist()],
                                           dispersion[eig_key][ns][nb][branch], c=colour,
                                           ls=kwargs['ls'][seed_ind], alpha=alpha, label=label)

    if len(seeds) > 1:
        disp_legend = ax_dispersion.legend(loc='upper center',
                                           frameon=True, fancybox=False, shadow=False, framealpha=1)
        bbox_extra_artists.append(disp_legend)

    ax_dispersion.axhline(0, ls='--', lw=1, c='grey')
    ax_dispersion.set_ylim(kwargs['plot_window'])
    if kwargs['phonons']:
        ylabel = 'Wavenumber (cm$^{-1}$)'
    else:
        ylabel = r'Energy (eV)'
    ax_dispersion.set_ylabel(ylabel)
    ax_dispersion.set_xlim(0, 1)
    _get_path_labels(seed, dispersion, ax_dispersion, path, path_key, branch_key, seed_ind, kwargs)

    return ax_dispersion


def dos_plot(seeds, ax_dos, kwargs, bbox_extra_artists):
    """ Plot a density of states on the given axis. Will detect
    pDOS and spin-dependent DOS data automatically.

    Parameters:
        seeds (list): the seednames of the data to plot.
        ax_dos (matplotlib.Axes): the axis to plot on.
        kwargs (dict): any plotting keywords (from e.g. dispersion script).
        bbox_extra_artists (list): a list to which to append legends.

    Returns:
        matplotlib.Axes: the axis that was plotted on.

    """
    from matador.scrapers import optados2dict, phonon2dict, bands2dict
    for seed_ind, seed in enumerate(seeds):
        seed = seed.replace('.bands', '').replace('.phonon', '')
        if kwargs['plot_dos']:
            if not kwargs['phonons']:
                if kwargs.get('dos') is None:
                    # look for dat files, and just use the first
                    exts = ['adaptive.dat', 'fixed.dat', 'linear.dat', 'bands_dos']
                    for ext in exts:
                        if os.path.isfile('{}.{}'.format(seed, ext)):
                            dos_seed = '{}.{}'.format(seed, ext)
                            break
                    else:
                        raise SystemExit('No total DOS files found.')
                else:
                    dos_seed = kwargs.get('dos')

                if dos_seed.endswith('.bands_dos'):
                    # if bands_dos exists, do some manual broadening
                    dos_data, s = bands2dict(dos_seed)
                    raw_weights = []
                    space_size = 1000
                    gaussian_width = kwargs.get('gaussian_width')
                    if gaussian_width is None:
                        gaussian_width = 0.1

                    raw_eigenvalues = []
                    for kind, qpt in enumerate(dos_data['eigenvalues_k_s']):
                            weight = dos_data['kpoint_weights'][kind]
                            for eig in qpt:
                                raw_weights.append(weight)
                                raw_eigenvalues.append(eig)
                    raw_eigenvalues = np.asarray(raw_eigenvalues)
                    hist, energies = np.histogram(raw_eigenvalues, bins=space_size)
                    # shift bin edges to bin centres
                    energies -= energies[1] - energies[0]
                    energies = energies[:-1]
                    new_energies = np.reshape(energies, (1, len(energies)))
                    new_energies = new_energies - np.reshape(energies, (1, len(energies))).T
                    dos = np.sum(hist * np.exp(-(new_energies)**2 / gaussian_width), axis=1)
                    dos = np.divide(dos, np.sqrt(2 * np.pi * gaussian_width**2))
                    dos_data['dos'] = dos
                    dos_data['energies'] = energies
                else:
                    dos_data, s = optados2dict(dos_seed, verbosity=0)

                if not s:
                    raise RuntimeError(dos_data)

                energies = dos_data['energies']
                dos = dos_data['dos']

                if kwargs['plot_window'] is None:
                    kwargs['plot_window'] = [-10, 10]

                if 'spin_dos' in dos_data:
                    max_density = max(np.max(np.abs(dos_data['spin_dos']['down'][np.where(energies > kwargs['plot_window'][0])])),
                                      np.max(np.abs(dos_data['spin_dos']['up'][np.where(energies > kwargs['plot_window'][0])])))
                else:
                    max_density = np.max(dos[np.where(np.logical_and(energies < kwargs['plot_window'][1], energies > kwargs['plot_window'][0]))])

                pdos_seed = '{}.pdos.dat'.format(seed)
                pdos_data = {}
                if os.path.isfile(pdos_seed):
                    pdos_data, s = optados2dict(pdos_seed, verbosity=0)
                    if not s:
                        raise RuntimeError(pdos_data)
                    dos_data['pdos'] = pdos_data
            else:
                if not os.path.isfile(seed + '.phonon_dos'):
                    phonon_data, s = phonon2dict(seed + '.phonon')
                    if not s:
                        raise RuntimeError(phonon_data)
                    else:
                        if kwargs['plot_window'] is None:
                            kwargs['plot_window'] = [min(-10, np.min(phonon_data['eigenvalues_q']) - 10), np.max(phonon_data['eigenvalues_q'])]
                        space_size = 1000
                        gaussian_width = kwargs.get('gaussian_width', 100)
                        raw_weights = []
                        raw_eigenvalues = []
                        for qind, qpt in enumerate(phonon_data['eigenvalues_q']):
                            weight = phonon_data['qpoint_weights'][qind]
                            for eig in qpt:
                                raw_weights.append(weight)
                                raw_eigenvalues.append(eig)
                        hist, energies = np.histogram(raw_eigenvalues, weights=raw_weights, bins=space_size)
                        # shift bin edges to bin centres
                        energies -= energies[1] - energies[0]
                        energies = energies[:-1]
                        new_energies = np.reshape(energies, (1, len(energies)))
                        new_energies -= np.reshape(energies, (1, len(energies))).T
                        dos = np.sum(hist * np.exp(-(new_energies)**2 / gaussian_width), axis=1)
                        dos = np.divide(dos, np.sqrt(2 * np.pi * gaussian_width**2))
                        max_density = np.max(dos)
                        phonon_data['freq_unit'] = phonon_data['freq_unit'].replace('-1', '$^{-1}$')
                        ax_dos.axvline(phonon_data['softest_mode_freq'], ls='--', c='r',
                                       label=(r'$\omega_\mathrm{{min}} = {:5.3f}$ {}'
                                              .format(phonon_data['softest_mode_freq'],
                                                      phonon_data['freq_unit'])))
                else:
                    with open(seed + '.phonon_dos', 'r') as f:
                        flines = f.readlines()
                    for ind, line in enumerate(flines):
                        if 'begin dos' in line.lower():
                            projector_labels = line.split()[5:]
                            projector_labels = [(label, None) for label in projector_labels]
                            begin = ind + 1
                            break
                    data_flines = flines[begin:-1]
                    with open(seed + '.phonon_dos_tmp', 'w') as f:
                        for line in data_flines:
                            f.write(line + '\n')
                    raw_data = np.loadtxt(seed + '.phonon_dos_tmp')
                    energies = raw_data[:, 0]
                    dos = raw_data[:, 1]
                    dos_data = {}
                    dos_data['dos'] = dos
                    max_density = np.max(dos)
                    dos_data['energies'] = energies
                    if kwargs['plot_window'] is None:
                        kwargs['plot_window'] = [np.min(energies[np.where(dos > 1e-3)]) - 10, np.max(energies[np.where(dos > 1e-3)])]
                    dos_data['pdos'] = dict()
                    for i, label in enumerate(projector_labels):
                        dos_data['pdos'][label] = raw_data[:, i + 2]
                    pdos = dos_data['pdos']
                    pdos_data = dos_data
                    from os import remove
                    remove(seed + '.phonon_dos_tmp')

            if kwargs['phonons']:
                ylabel = 'Phonon DOS'
                xlabel = 'Wavenumber (cm$^{{-1}}$)'
            else:
                if kwargs['plot_bandstructure']:
                    ylabel = 'DOS'
                else:
                    ylabel = 'DOS (eV$^{{-1}}$Å$^{{-3}}$)'
                xlabel = 'Energy (eV)'

            if len(seeds) > 1:
                colour = kwargs['seed_colours'][seed_ind]
            else:
                colour = None

            ax_dos.grid(False)

            if kwargs['plot_bandstructure']:
                ax_dos.set_xticks([0.6 * max_density])
                ax_dos.set_xticklabels([ylabel])
                ax_dos.axhline(0, c='grey', ls='--', lw=1)
                if 'spin_dos' in dos_data:
                    ax_dos.set_xlim(-max_density*1.2, max_density * 1.2)
                else:
                    ax_dos.set_xlim(0, max_density * 1.2)
                ax_dos.set_ylim(kwargs['plot_window'])
                ax_dos.axvline(0, c='grey', lw=1)
                ax_dos.xaxis.set_ticks_position('none')

                if 'spin_dos' not in dos_data:
                    ax_dos.plot(dos, energies, ls=kwargs['ls'][seed_ind],
                                color='grey', zorder=1e10, label='Total DOS')
                    if 'pdos' not in dos_data:
                        ax_dos.fill_betweenx(energies[np.where(energies > 0)], 0, dos[np.where(energies > 0)], alpha=0.2, color=kwargs['conduction'])
                        ax_dos.fill_betweenx(energies[np.where(energies <= 0)], 0, dos[np.where(energies <= 0)], alpha=0.2, color=kwargs['valence'])

            else:
                ax_dos.set_xlabel(xlabel)
                ax_dos.set_ylabel(ylabel)
                ax_dos.axvline(0, c='grey', lw=1, ls='--')
                if 'spin_dos' in dos_data:
                    ax_dos.set_ylim(-max_density*1.2, max_density * 1.2)
                else:
                    ax_dos.set_ylim(0, max_density * 1.2)
                ax_dos.set_xlim(kwargs['plot_window'])
                ax_dos.axhline(0, c='grey', lw=1)

                if 'spin_dos' not in dos_data:
                    ax_dos.plot(energies, dos, ls=kwargs['ls'][seed_ind], alpha=1,
                                c='grey', zorder=1e10, label='Total DOS')
                    if 'pdos' not in dos_data:
                        ax_dos.fill_between(energies[np.where(energies > 0)], 0, dos[np.where(energies > 0)], alpha=0.2, color=kwargs['conduction'])
                        ax_dos.fill_between(energies[np.where(energies <= 0)], 0, dos[np.where(energies <= 0)], alpha=0.2, color=kwargs['valence'])

            if 'pdos' in pdos_data and len(seeds) == 1:
                pdos = pdos_data['pdos']
                energies = pdos_data['energies']
                projector_labels, dos_colours = _get_projector_info([projector for projector in pdos])
                for ind, projector in enumerate(pdos):
                    if ind == 0:
                        stack = np.zeros_like(pdos[projector])

                    if not kwargs['no_stacked_pdos']:
                        alpha = 0.8
                    else:
                        alpha = 0.7

                    # mask negative contributions with 0
                    pdos[projector] = np.ma.masked_where(pdos[projector] < 0, pdos[projector], copy=True)
                    np.ma.set_fill_value(pdos[projector], 0)
                    pdos[projector] = np.ma.filled(pdos[projector])

                    if not np.max(pdos[projector]) < 1e-8:

                        if kwargs['plot_bandstructure']:
                            # ax_dos.plot(stack+pdos[projector], energies, lw=1, zorder=1000, color=dos_colours[ind])
                            if not kwargs['no_stacked_pdos']:
                                ax_dos.fill_betweenx(energies, stack, stack+pdos[projector],
                                                     alpha=alpha, label=projector_labels[ind],
                                                     color=dos_colours[ind])
                        else:
                            # ax_dos.plot(energies, stack+pdos[projector], lw=1, zorder=1000, color=dos_colours[ind])
                            if not kwargs['no_stacked_pdos']:
                                ax_dos.fill_between(energies, stack, stack+pdos[projector],
                                                    alpha=alpha, label=projector_labels[ind],
                                                    color=dos_colours[ind])

                        if not kwargs['no_stacked_pdos']:
                            stack += pdos[projector]

                if not kwargs['pdos_hide_tot'] and not kwargs['no_stacked_pdos']:
                    if kwargs['plot_bandstructure']:
                        ax_dos.plot(stack, energies,
                                    ls='--', alpha=1, color='black', zorder=1e10, label='Sum pDOS')
                    else:
                        ax_dos.plot(energies, stack,
                                    ls='--', alpha=1, color='black', zorder=1e10, label='Sum pDOS')

            elif 'spin_dos' in dos_data:
                print('Plotting spin dos')
                if kwargs['plot_bandstructure']:
                    if not kwargs.get('spin_only') == 'up':
                        ax_dos.fill_betweenx(energies, 0, dos_data['spin_dos']['down'], alpha=0.2, color='b')
                        ax_dos.plot(dos_data['spin_dos']['down'], energies, ls=kwargs['ls'][seed_ind], color='b', zorder=1e10, label='spin-down channel', alpha=alpha)
                    elif not kwargs.get('spin_only') == 'down':
                        ax_dos.fill_betweenx(energies, 0, dos_data['spin_dos']['up'], alpha=0.2, color='r')
                        ax_dos.plot(dos_data['spin_dos']['up'], energies, ls=kwargs['ls'][seed_ind], color='r', zorder=1e10, label='spin-up channel', alpha=alpha)
                else:
                    if not kwargs.get('spin_only') == 'up':
                        ax_dos.plot(energies, dos_data['spin_dos']['down'], ls=kwargs['ls'][seed_ind], color='b', zorder=1e10, label='spin-down channel')
                        ax_dos.fill_between(energies, 0, dos_data['spin_dos']['down'], alpha=0.2, color='b')
                    elif not kwargs.get('spin_only') == 'down':
                        ax_dos.plot(energies, dos_data['spin_dos']['up'], ls=kwargs['ls'][seed_ind], color='r', zorder=1e10, label='spin-up channel')
                        ax_dos.fill_between(energies, 0, dos_data['spin_dos']['up'], alpha=0.2, color='r')

            if len(seeds) == 1:
                if kwargs['plot_bandstructure']:
                    dos_legend = ax_dos.legend(bbox_to_anchor=(1, 1),
                                               frameon=True, fancybox=False, shadow=False)
                else:
                    dos_legend = ax_dos.legend(frameon=True, fancybox=False, shadow=False)
                bbox_extra_artists.append(dos_legend)

    return ax_dos


def projected_bandstructure_plot(seed, ax, path, dispersion, bbox_extra_artists, mode='scatter', **kwargs):
    """ Plot projected bandstructure with weightings from OptaDOS pdis.dat file.

    Parameters:
        seed (str): seed name for files to scrape.
        ax (matplotlib.pyplot.Axes): axis to plot on.
        dispersion (dict): scraped bandstructure info without weights.
        bbox_extra_artists (list): list to append any legends too.

    Keyword arguments:
        mode (str): either 'scatter' or 'rgb' for two plotting options.

    Returns:
        matplotlib.pyplot.Axes: the axis that was plotted on.

    """
    from matador.scrapers.castep_scrapers import optados2dict, get_kpt_branches
    from matador.utils.cell_utils import frac2cart, real2recip
    seed = seed.replace('.pdis.dat', '')
    dos_data, s = optados2dict(seed + '.pdis.dat', verbosity=0)
    if not s:
        raise RuntimeError(dos_data)

    pdis = np.asarray(dos_data['pdis'])
    pdis[pdis < 0] = 0
    pdis[pdis > 1] = 1

    projectors = dos_data['projectors']
    keep_inds = []
    for ind, projector in enumerate(projectors):
        if np.max(pdis[:, :, ind]) > 1e-8:
            keep_inds.append(ind)

    if len(keep_inds) <= 3:
        mode = 'rgb'
    else:
        mode = 'scatter'
    mode = 'scatter'

    lattice_cart = dispersion['lattice_cart']
    eigs = np.asarray(dos_data['eigenvalues'])

    projector_labels, dos_colours = _get_projector_info(projectors)

    counter = 0
    for ind, projector in enumerate(projectors):
        if ind in keep_inds:
            if mode == 'scatter':
                ax.scatter(1e20, 0, facecolor=(1,1,1,0), edgecolor=dos_colours[ind], label=projector_labels[ind], lw=1)
            else:
                colours = ['red', 'blue', 'green']
                ax.plot([1e20, 1e20], [0, 0], c=colours[counter], label=projector_labels[ind], lw=3, alpha=0.8)
                counter += 1

    try:
        from tqdm import tqdm
    except ImportError:
        def tqdm(x):
            return x
        pass

    dos_data['kpoints_cartesian'] = np.asarray(frac2cart(real2recip(lattice_cart), dos_data['kpoints']))
    dos_data['kpoint_branches'], dos_data['kpoint_path_spacing'] = get_kpt_branches(dos_data['kpoints_cartesian'])
    for nb in tqdm(range(dos_data['num_bands'])):
        if mode == 'scatter':
            for branch_ind, branch in enumerate(dos_data['kpoint_branches']):
                _ordered_scatter(path[(np.asarray(branch) - branch_ind).tolist()],
                                 eigs[branch, nb], pdis[branch, nb], ax=ax, colours=[dos_colours[ind] for ind in keep_inds], zorder=0)
        elif mode == 'rgb':
            for branch_ind, branch in enumerate(dos_data['kpoint_branches']):
                red = pdis[branch, nb, 0]
                if np.shape(pdis)[-1] > 1:
                    blue = pdis[branch, nb, 1]
                else:
                    blue = np.zeros_like(red)
                if np.shape(pdis)[-1] > 2:
                    green = pdis[branch, nb, 2]
                else:
                    green = np.zeros_like(red)
                _rgbline(path[(np.asarray(branch) - branch_ind).tolist()],
                         eigs[branch, nb], red, green, blue, ax=ax, zorder=0)

    l = ax.legend(loc=1)
    l.set_zorder(1e20)
    bbox_extra_artists.append(l)
    return ax


def _rgbline(k, e, red, green, blue, alpha=1, ax=None, zorder=None, interpolation_factor=10):
    """ Draw a line coloured by three components. Based on:
    http://nbviewer.ipython.org/urls/raw.github.com/dpsanders/matplotlib-examples/master/colorline.ipynb
    """
    from matplotlib.collections import LineCollection
    from scipy.interpolate import interp1d
    ek_fn = interp1d(k, e)
    k_interp = np.linspace(np.min(k), np.max(k), num=int(interpolation_factor*len(k)))
    k_interp2 = np.linspace(np.min(k)+0.0001, np.max(k), num=int(interpolation_factor*len(k)))
    ek_interp = ek_fn(k_interp)
    ek_interp2 = ek_fn(k_interp2)
    red = interp1d(k, red)(k_interp)
    blue = interp1d(k, blue)(k_interp)
    green = interp1d(k, green)(k_interp)
    left = np.array([k_interp, ek_interp]).T.reshape(-1, 1, 2)
    right = np.array([k_interp2, ek_interp2]).T.reshape(-1, 1, 2)
    seg = np.concatenate([left[:-1], right[1:]], axis=1)
    nseg = len(k_interp)-1
    r = [0.5*(red[i]+red[i+1]) for i in range(nseg)]
    g = [0.5*(green[i]+green[i+1]) for i in range(nseg)]
    b = [0.5*(blue[i]+blue[i+1]) for i in range(nseg)]
    widths = np.asarray(r+g+b) * 10 + 1
    a = 2 * np.asarray(r+g+b) + 0.5
    a[a >= 1] = 1
    try:
        lc = LineCollection(seg, colors=list(zip(r, g, b, a)), linewidths=widths, zorder=zorder)
    except Exception as exc:
        print(r, g, b)
        raise exc
    if ax is not None:
        ax.add_collection(lc)


def _ordered_scatter(k, e, projections, alpha=1, ax=None, zorder=None, colours=None, interpolation_factor=10):
    """ WIP: Try to plot a scatter of PDIS points. """
    from scipy.interpolate import interp1d
    ek_fn = interp1d(k, e)

    k_interp = np.linspace(np.min(k), np.max(k), num=int(interpolation_factor*len(k)))
    ek_interp = ek_fn(k_interp)
    projections = projections.T
    interp_projections = []
    for i, proj in enumerate(projections):
        interp_projections.append(interp1d(k, projections[i])(k_interp))
    interp_projections = np.asarray(interp_projections)
    pts = np.array([k_interp, ek_interp]).T.reshape(-1, 1, 2)

    from copy import deepcopy
    cat_pts = deepcopy(pts)
    flat_colours = np.zeros_like(interp_projections[0], dtype=int)
    flat_projections = deepcopy(interp_projections[0])
    for i in range(len(projections)-1):
        # pts[:, 0, 1] += 0.1
        cat_pts = np.concatenate((cat_pts, pts), axis=0)
        flat_colours = np.concatenate((flat_colours, np.ones_like(projections[i])*(i+1)))
        flat_projections = np.concatenate((flat_projections, projections[i+1]))

    cat_pts = cat_pts[np.argsort(flat_projections)]
    flat_colours = flat_colours[np.argsort(flat_projections)].tolist()
    flat_projections.sort()
    colours = [colours[int(i)] for i in flat_colours]
    cat_pts = cat_pts[::-1]
    flat_projections = flat_projections[::-1]
    colours = list(reversed(colours))
    ax.scatter(cat_pts[:, 0, 0], cat_pts[:, 0, 1], s=50*flat_projections**2, edgecolor=colours, lw=1, facecolor=None, alpha=0.8)
    ax.plot(pts[:, 0, 0], pts[:, 0, 1], lw=0.5, alpha=0.5)


def match_bands(dispersion, branches):
    """ Recursively reorder eigenvalues such that bands join up correctly,
    based on local gradients.

    Parameters:
        dispersion (numpy.ndarray): array containing eigenvalues as a
            function of q/k
        branches (:obj:`list` of :obj:`int`): list containing branches of
            k/q-point path

    Returns:
        numpy.ndarray: reordered branches.

    """
    from copy import deepcopy

    for channel_ind, channel in enumerate(dispersion):
        eigs = channel
        for branch_ind, branch in enumerate(branches):
            eigs_branch = eigs[:, branch]
            converged = False
            counter = 0
            i_cached = 0
            while not converged and counter < len(branch):
                counter += 1
                for i in range(i_cached+1, len(branch) - 1):
                    guess = (2 * eigs_branch[:, i] - eigs_branch[:, i-1])
                    argsort_guess = np.argsort(guess)
                    if np.any(np.argsort(guess) != np.argsort(eigs_branch[:, i+1])):
                        tmp_copy = deepcopy(eigs)
                        for ind, mode in enumerate(np.argsort(eigs_branch[:, i]).tolist()):
                            eigs_branch[mode, i+1:] = tmp_copy[:, branch][argsort_guess[ind], i+1:]
                        for other_branch in branches[branch_ind:]:
                            eigs_other_branch = eigs[:, other_branch]
                            for ind, mode in enumerate(np.argsort(eigs_branch[:, i]).tolist()):
                                eigs_other_branch[mode] = tmp_copy[:, other_branch][argsort_guess[ind]]
                            eigs[:, other_branch] = eigs_other_branch
                        eigs[:, branch] = eigs_branch
                        i_cached = i
                        break

                    if i == len(branch) - 2:
                        converged = True

        dispersion[channel_ind] = eigs.reshape(1, len(eigs), len(eigs[0]))

    return dispersion


def _linearise_path(dispersion, path_key, branch_key, num_key, kwargs):
    """ For a given k-point path, normalise the spacing between points, mapping
    it onto [0, 1].

    Note:
        If kwargs['preserve_kspace-distance'], point separation will be determined
        by their actual separation in reciprocal space, otherwise they will be
        equally spaced.

    Returns:
        np.ndarray: 3xN array containing k-points mapped onto [0, 1].

    """
    path = [0]
    for branch in dispersion[branch_key]:
        for ind, kpt in enumerate(dispersion[path_key][branch]):
            if ind != len(branch) - 1:
                if kwargs['preserve_kspace_distance']:
                    diff = np.sqrt(np.sum((kpt - dispersion[path_key][branch[ind + 1]])**2))
                else:
                    diff = 1.
                path.append(path[-1] + diff)
    path = np.asarray(path)
    path /= np.max(path)
    assert len(path) == int(dispersion[num_key]) - len(dispersion[branch_key]) + 1

    return path


def _get_lineprops(dispersion, eig_key, spin_key, nb, ns, branch, branch_ind, seed_ind, kwargs):
    """ Get the properties of the line to plot. """
    colour = None
    alpha = 1
    label = None
    if not kwargs['phonons']:
        if dispersion[spin_key] == 2:
            if ns == 0:
                colour = 'red'
                alpha = 0.3
            else:
                colour = 'blue'
                alpha = 0.3
        else:
            if kwargs.get('band_colour') == 'occ':
                band_min = np.min(dispersion[eig_key][ns][nb][branch])
                band_max = np.max(dispersion[eig_key][ns][nb][branch])
                if band_max < 0:
                    colour = kwargs.get('valence')
                elif band_min > 0:
                    colour = kwargs.get('conduction')
                elif band_min < 0 < band_max:
                    colour = kwargs.get('crossing')

    if kwargs['colour_by_seed']:
        colour = kwargs.get('seed_colours')[seed_ind]

    if kwargs.get('band_colour') is not None:
        if kwargs.get('band_colour') != 'occ':
            colour = kwargs.get('band_colour')

    if kwargs.get('highlight_bands') is not None:
        if nb in kwargs.get('highlight_bands'):
            colour = 'red'
        else:
            alpha = 0.5
    if branch_ind == 0 and ns == 0 and nb == 0 and kwargs.get('labels') is not None:
        label = kwargs.get('labels')[seed_ind]

    return colour, alpha, label


def _get_path_labels(seed, dispersion, ax_dispersion, path, path_key, branch_key, seed_ind, kwargs):
    """ Scrape k-point path labels from cell file and seekpath. """
    from matador.scrapers import cell2dict, res2dict
    from matador.utils.cell_utils import doc2spg
    from seekpath import get_path
    xticks = []
    xticklabels = []
    shear_planes = []
    labelled = []

    # get dispersion path labels
    spg_structure = None
    if kwargs['phonons']:
        spg_structure = doc2spg(dispersion)
    else:
        res = False
        cell = False
        if os.path.isfile(seed + '.res'):
            res = True
        elif os.path.isfile(seed + '.cell'):
            cell = True
        else:
            print('Failed to find {}.cell or {}.res, will not be able to generate labels.'.format(seed, seed))

        success = False
        if cell:
            doc, success = cell2dict(seed + '.cell',
                                     db=False, verbosity=kwargs.get('verbosity', 0),
                                     outcell=True, positions=True)
        if res and not success:
            doc, success = res2dict(seed + '.res',
                                    db=False, verbosity=kwargs.get('verbosity', 0))
        if success:
            spg_structure = doc2spg(doc)
        else:
            print('Failed to scrape {}.cell/.res, will not be able to generate labels.'.format(seed))

    if spg_structure is not False and spg_structure is not None:
        seekpath_results = get_path(spg_structure)
        path_labels = seekpath_results['point_coords']

    for branch_ind, branch in enumerate(dispersion[branch_key]):
        for sub_ind, ind in enumerate(branch):
            kpt = dispersion[path_key][ind]
            for label, point in path_labels.items():
                if np.allclose(point, kpt):
                    if ind - branch_ind not in labelled:
                        label = label.replace('GAMMA', r'\Gamma')
                        label = label.replace('SIGMA', r'\Sigma')
                        label = label.replace('DELTA', r'\Delta')
                        label = label.replace('LAMBDA', r'\Lambda')
                        if sub_ind == len(branch) - 1:
                            if branch_ind < len(dispersion[branch_key]) - 1:
                                _tmp = dispersion[path_key]
                                next_point = _tmp[dispersion[branch_key][branch_ind + 1][0]]
                                for new_label, new_point in path_labels.items():
                                    new_label = new_label.replace('GAMMA', r'\Gamma')
                                    new_label = new_label.replace('SIGMA', r'\Sigma')
                                    new_label = new_label.replace('DELTA', r'\Delta')
                                    new_label = new_label.replace('LAMBDA', r'\Lambda')
                                    if np.allclose(new_point, next_point):
                                        label = '{}|{}'.format(label, new_label)
                                        ax_dispersion.axvline(path[ind - branch_ind], ls='-', c='grey', zorder=1, lw=0.5)
                                        labelled.append(ind - branch_ind)
                                        shear_planes.append(ind)
                        label = '${}$'.format(label)
                        ax_dispersion.axvline(path[ind - branch_ind], ls='--', c='grey', zorder=0, lw=0.5)
                        xticklabels.append(label)
                        xticks.append(path[ind - branch_ind])
                        break

    if not kwargs['phonons'] and kwargs['gap'] and dispersion['band_gap'] > 0:
        vbm_pos = dispersion['band_gap_path_inds'][1]
        vbm = dispersion['valence_band_min']
        cbm_pos = dispersion['band_gap_path_inds'][0]
        cbm = dispersion['conduction_band_max']
        if vbm_pos != cbm_pos:
            vbm_offset = sum([vbm_pos > ind for ind in shear_planes])
            cbm_offset = sum([cbm_pos > ind for ind in shear_planes])
            ax_dispersion.plot([path[vbm_pos - vbm_offset], path[cbm_pos - cbm_offset]], [vbm, cbm],
                               ls=kwargs['ls'][seed_ind],
                               c='blue',
                               label='indirect gap {:3.3f} eV'.format(cbm - vbm))

        vbm_pos = dispersion['direct_gap_path_inds'][1]
        vbm = dispersion['direct_valence_band_min']
        cbm_pos = dispersion['direct_gap_path_inds'][0]
        cbm = dispersion['direct_conduction_band_max']
        vbm_offset = sum([vbm_pos > ind for ind in shear_planes])
        cbm_offset = sum([cbm_pos > ind for ind in shear_planes])
        ax_dispersion.plot([path[vbm_pos - vbm_offset], path[cbm_pos - cbm_offset]], [vbm, cbm],
                           ls=kwargs['ls'][seed_ind],
                           c='red',
                           label='direct gap {:3.3f} eV'.format(cbm - vbm))
        ax_dispersion.legend(loc='upper center',
                             bbox_to_anchor=(0.5, 1.1),
                             fancybox=True, shadow=True,
                             ncol=2, handlelength=1)

    if seed_ind == 0:
        ax_dispersion.set_xticks(xticks)
        ax_dispersion.set_xticklabels(xticklabels)
        ax_dispersion.grid(False)


def _get_projector_info(projectors):
    """ Grab appropriate colours and labels from
    a list of projectors.

    Parameters:
        projectors (list): list containing (element_str, l_channel) tuples.

    Returns:
        list: list of projector labels, e.g. {element_str}-${l_channel}$.
        list: list of colours for density of states, derived from vesta colours.

    """

    import matplotlib.pyplot as plt
    element_colours = get_element_colours()
    projector_labels = []
    dos_colours = []
    for ind, projector in enumerate(projectors):
        if projector[0] is None:
            projector_label = '${}$-character'.format(projector[1])
        elif projector[1] is None:
            projector_label = projector[0]
        else:
            projector_label = '{p[0]} (${p[1]}$)'.format(p=projector)
        projector_labels.append(projector_label)

        # if species-projected only, then use VESTA colours
        if projector[0] is not None and projector[1] is None:
            dos_colours.append(element_colours.get(projector[0]))
        # if species_ang-projected, then use VESTA colours but lightened
        elif projector[0] is not None and projector[1] is not None:
            from copy import deepcopy
            dos_colour = deepcopy(element_colours.get(projector[0]))
            multi = ['s', 'p', 'd', 'f'].index(projector[1]) - 1
            for jind, _ in enumerate(dos_colour):
                dos_colour[jind] = max(min(dos_colour[jind]+multi*0.2, 1), 0)
            dos_colours.append(dos_colour)
        # otherwise if just ang-projected, use colour_cycle
        else:
            dos_colours.append(list(plt.rcParams['axes.prop_cycle'].by_key()['color'])[ind])

    return projector_labels, dos_colours