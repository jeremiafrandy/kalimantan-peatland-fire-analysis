"""Download the two public source snapshots and verify their recorded hashes."""
from __future__ import annotations
import argparse, hashlib, json, urllib.parse, urllib.request
from pathlib import Path

MAP_BASE='https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/6/query'
MAP_PARAMS={'f':'geojson','where':"landform LIKE '%Gambut%'",'geometry':'108,-5,120,5',
    'geometryType':'esriGeometryEnvelope','inSR':'4326','outSR':'4326',
    'spatialRel':'esriSpatialRelIntersects','outFields':'*','returnGeometry':'true','orderByFields':'objectid'}
SENSOR_URL='https://zenodo.org/records/13767528/files/PA_data.nc?download=1'
MAP_SHA256='38bc876ecb68d6991e7bfa62edcb2f564037ee23bb14c7cef930b9da117c96b2'
SENSOR_MD5='e811953a84db4fd14a33f67dd8f483dd'

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('data/source'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    jobs=[('BIG_ID6.geojson',MAP_BASE+'?'+urllib.parse.urlencode(MAP_PARAMS),'sha256',MAP_SHA256),
          ('PA_data.nc',SENSOR_URL,'md5',SENSOR_MD5)]
    results=[]
    for name,url,algorithm,expected in jobs:
        with urllib.request.urlopen(url,timeout=90) as f:raw=f.read()
        digest=hashlib.new(algorithm,raw).hexdigest()
        if digest != expected: raise ValueError(f'{name}: source changed; expected {expected}, received {digest}. Do not silently substitute it.')
        if name.endswith('.geojson'):
            d=json.loads(raw); assert len(d['features'])==100
        (a.output/name).write_bytes(raw)
        results.append({'file':name,'algorithm':algorithm,'hash':digest,'bytes':len(raw)})
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
