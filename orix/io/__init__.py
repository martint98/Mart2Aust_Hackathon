# -*- coding: utf-8 -*-
# Copyright 2018-2022 the orix developers
#
# This file is part of orix.
#
# orix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# orix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with orix.  If not, see <http://www.gnu.org/licenses/>.

"""Load and save utilities."""

import os
from warnings import warn

from h5py import File, is_hdf5
import numpy as np

from orix.io.plugins import plugin_list
from orix.io.plugins._h5ebsd import hdf5group2dict


extensions = [plugin.file_extensions for plugin in plugin_list if plugin.writes]


# Lists what will be imported when calling "from orix.io import *"
__all__ = [
    "loadang",
    "loadctf",
    "load",
    "save",
]


def loadang(file_string):
    """Load ``.ang`` files.

    Parameters
    ----------
    file_string : str
        Path to the ``.ang`` file. This file is assumed to list the Euler
        angles in the Bunge convention in the first three columns.

    Returns
    -------
    Rotation

    """
    from orix.quaternion.rotation import Rotation

    data = np.loadtxt(file_string)
    euler = data[:, :3]
    rotation = Rotation.from_euler(euler)
    return rotation


def loadctf(file_string):
    """Load ``.ang`` files.

    Parameters
    ----------
    file_string : str
        Path to the ``.ctf`` file. This file is assumed to list the Euler
        angles in the Bunge convention in the columns 5, 6, and 7.

    Returns
    -------
    Rotation

    """

    from orix.quaternion.rotation import Rotation

    data = np.loadtxt(file_string, skiprows=17)[:, 5:8]
    euler = np.radians(data)
    rotation = Rotation.from_euler(euler)
    return rotation


def load(filename, **kwargs):
    """Load data from a supported file.

    Parameters
    ----------
    filename : str
        Name of file to load.
    kwargs
        Keyword arguments passed to the corresponding orix reader. See
        their individual docstrings for available arguments.

    Returns
    -------
    data : CrystalMap
        Crystal map read from the file.
    """
    if not os.path.isfile(filename):
        raise IOError(f"No filename matches '{filename}'.")

    # Find matching reader for file extension
    extension = os.path.splitext(filename)[1][1:]
    readers = []
    for plugin in plugin_list:
        if extension.lower() in plugin.file_extensions:
            readers.append(plugin)

    n_matching_readers = len(readers)
    if n_matching_readers == 0:
        raise IOError(
            f"Could not read '{filename}'. If the file format is supported, please "
            "report this error."
        )
    elif n_matching_readers > 1 and is_hdf5(filename):
        reader = _plugin_from_manufacturer(filename, readers)
    else:
        reader = readers[0]

    return reader.file_reader(filename, **kwargs)


def _plugin_from_manufacturer(filename, plugins):
    """Return the correct plugin based on the manufacturer listed in a
    top group named 'Manufacturer' in an HDF5 file.

    Parameters
    ----------
    filename : str
        Name of the file to find the correct plugin for.
    plugins : list
        List of potential HDF5 plugins.

    Returns
    -------
    matching_plugin
        One of the potential plugins, or None if no matching plugin was
        found.
    """
    with File(filename, mode="r") as f:
        d = hdf5group2dict(f["/"])
        manufacturer = None
        for key, value in d.items():
            if key.lower() == "manufacturer":
                manufacturer = value
        matching_plugin = None
        for p in plugins:
            if (
                hasattr(p, "manufacturer")
                and manufacturer is not None
                and p.manufacturer in manufacturer
            ):
                matching_plugin = p
    return matching_plugin


def save(filename, object2write, overwrite=None, **kwargs):
    """Write data to a supported file format.

    Parameters
    ----------
    filename : str
        Name of file to write to.
    object2write : CrystalMap
        Object to write to file.
    overwrite : bool, optional
        If None and the file exists, the user is queried. If True (False)
        the file is (not) overwritten if it exists.
    kwargs
        Keyword arguments passed to the corresponding orix writer. See
        their individual docstrings for available arguments.
    """
    ext = os.path.splitext(filename)[1][1:]

    writer = None
    for p in plugin_list:
        if (
            ext.lower() in p.file_extensions
            and p.writes
            and isinstance(object2write, p.writes_this)
        ):
            writer = p
            break

    if writer is None:
        raise IOError(
            f"'{ext}' does not correspond to any supported format. Supported "
            f"file extensions are: '{extensions}'."
        )
    else:
        is_file = os.path.isfile(filename)
        if overwrite is None:
            write = _overwrite_or_not(filename)  # Ask what to do
        elif overwrite is True or (overwrite is False and not is_file):
            write = True
        elif overwrite is False and is_file:
            write = False
        else:
            raise ValueError("`overwrite` parameter can only be None, True or False.")

    if write:
        writer.file_writer(filename, object2write, **kwargs)


def _overwrite_or_not(filename):
    """If the file exists, ask the user for overwriting and return True or
    False, else return True.

    This function is adapted from HyperSpy.

    Parameters
    ----------
    filename : str
        Name of file to write to.

    Returns
    -------
    overwrite : bool
        Whether to overwrite the file.
    """
    overwrite = True
    if os.path.isfile(filename):
        message = "Overwrite '%s' (y/n)?\n" % filename
        try:
            answer = input(message).lower()
            while (answer != "y") and (answer != "n"):
                print("Please answer y or n.")
                answer = input(message).lower()
            if answer == "n":
                overwrite = False
        except OSError:
            warn(
                "Not overwriting, since your terminal does not support raw input. To "
                "overwrite the file, use `overwrite=True`."
            )
            overwrite = False
    return overwrite
