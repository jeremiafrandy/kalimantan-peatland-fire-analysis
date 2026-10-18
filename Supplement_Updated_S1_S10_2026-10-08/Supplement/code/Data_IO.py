import ctypes, ctypes.util, json, os, struct
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from matplotlib.path import Path
def get_raster(path):
    """Return date strings and [day,row,col] float32 raster, retaining missing."""
    sizes = {2: 1, 3: 2, 4: 4, 12: 8, 16: 8}
    tags = {}
    with open(path, 'rb') as f:
        header = f.read(16)
        assert header[:4] == b'II+\0', 'Expected little-endian BigTIFF'
        f.seek(struct.unpack('<Q', header[8:])[0])
        n = struct.unpack('<Q', f.read(8))[0]
        for _ in range(n):
            raw = f.read(20)
            tag, typ, count, offset = struct.unpack('<HHQQ', raw)
            length = count * sizes.get(typ, 1)
            current = f.tell()
            if length <= 8:
                value = raw[12:12 + length]
            else:
                f.seek(offset)
                value = f.read(length)
                f.seek(current)
            tags[tag] = (typ, count, value)

    def numeric(tag, fmt):
        _, count, raw = tags[tag]
        return struct.unpack('<' + str(count) + fmt, raw)

    width, height, bands = [numeric(t, 'H')[0] for t in (256, 257, 277)]
    assert width == 120 and height == 101
    assert numeric(33550, 'd')[:2] == (0.1, 0.1)
    assert numeric(33922, 'd')[3:5] == (108., 5.)
    metadata = ET.fromstring(tags[42112][2].decode().rstrip('\0'))
    names = [i.text for i in metadata.findall('Item')
             if i.attrib.get('name') == 'DESCRIPTION']
    assert len(names) == bands and all(x.startswith('P_') for x in names)
    dates = pd.to_datetime([x[2:] for x in names], format='%Y%m%d')

    lib = ctypes.CDLL(ctypes.util.find_library('tiff'))
    lib.TIFFOpen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.TIFFOpen.restype = ctypes.c_void_p
    lib.TIFFTileSize64.argtypes = [ctypes.c_void_p]
    lib.TIFFTileSize64.restype = ctypes.c_uint64
    lib.TIFFReadEncodedTile.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                       ctypes.c_void_p, ctypes.c_ssize_t]
    lib.TIFFReadEncodedTile.restype = ctypes.c_ssize_t
    lib.TIFFClose.argtypes = [ctypes.c_void_p]
    tif = lib.TIFFOpen(os.fsencode(path), b'r')
    if not tif:
        raise OSError(f'Cannot read {path}')
    try:
        count = lib.TIFFTileSize64(tif)
        buffer = ctypes.create_string_buffer(count)
        assert lib.TIFFReadEncodedTile(tif, 0, buffer, count) == count
    finally:
        lib.TIFFClose(tif)
    tile = np.frombuffer(buffer, dtype='<f4').reshape(256, 256, bands)
    data = np.moveaxis(tile[:100, :120, :], -1, 0).copy()
    # The exported 101st row is outside the requested region and contains NaN.
    data[~np.isfinite(data) | (data == -9999)] = np.nan
    return dates, data


def hits(xy, geometry):
    """Boolean point-in-polygon for Polygon or MultiPolygon with holes."""
    result = np.zeros(len(xy), dtype=bool)
    polygons = (geometry['coordinates'] if geometry['type'] == 'MultiPolygon'
                else [geometry['coordinates']])
    for rings in polygons:
        exterior = np.asarray(rings[0], dtype=float)
        candidate = np.flatnonzero((xy[:, 0] >= exterior[:, 0].min()) &
                                   (xy[:, 0] <= exterior[:, 0].max()) &
                                   (xy[:, 1] >= exterior[:, 1].min()) &
                                   (xy[:, 1] <= exterior[:, 1].max()))
        if not candidate.size:
            continue
        inside = Path(exterior).contains_points(xy[candidate])
        indices = candidate[inside]
        for ring in rings[1:]:
            if indices.size:
                indices = indices[~Path(np.asarray(ring)).contains_points(xy[indices])]
        result[indices] = True
    return result


def province_and_peat(xy, provinces, peat_features):
    province = np.full(len(xy), '', dtype=object)
    for feature in provinces:
        province[hits(xy, feature['geometry'])] = feature['properties']['wadmpr']
    peat = np.zeros(len(xy), dtype=bool)
    for feature in peat_features:
        peat |= hits(xy, feature['geometry'])
    return province, peat

