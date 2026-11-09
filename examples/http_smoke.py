"""Check the exact migrated localhost server, not a historical instance."""
import http.client
import json
from pathlib import Path

def request(path, value=None):
    c = http.client.HTTPConnection('127.0.0.1', 8767, timeout=60)
    try:
        c.request('GET' if value is None else 'POST', path,
                  body=None if value is None else json.dumps(value),
                  headers={} if value is None else {'Content-Type': 'application/json'})
        r = c.getresponse()
        raw = r.read()
        assert r.status == 200, (path, r.status)
        return raw
    finally:
        c.close()

if __name__ == '__main__':
    checks = {p: len(request(p)) for p in ('/', '/map-app.js', '/map.css',
               '/vendor/leaflet.js', '/vendor/leaflet.css', '/regional-relief.png',
               '/regional-elevation.png')}
    catalog = json.loads(request('/api/catalog'))
    # Derive a request from the real server catalog; no recorded outputs.
    config = catalog['defaults']['regional']['rover']
    config['planning_method'] = 'fast'
    result = json.loads(request('/api/calculate', {'configuration': config, 'action': 'compare'}))
    alternatives = result['result']['alternatives']
    assert alternatives and alternatives[0]['status'] == 'SUCCESS', alternatives
    print(json.dumps(dict(checks=checks, calculation_id=result['calculation_id'],
        planning_method=result['planning_method'], status=alternatives[0]['status'],
        distance_m=alternatives[0]['plan']['total']['distance_m']), indent=2))
