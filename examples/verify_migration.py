"""Verify preserved source bytes and destination bytes against migration manifest."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'docs/migration/source-manifest.json').read_text(encoding='utf-8'))
source = root.parent / 'NASA-Sandbox-etapa01'
records = manifest['files']
changed_source, changed_target = [], []
for record in records:
    for base, changed in ((source, changed_source), (root, changed_target)):
        path = base / record['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            changed.append(record['path'])
print(json.dumps(dict(files=len(records), changed_source=changed_source,
                     changed_target=changed_target), indent=2))
raise SystemExit(bool(changed_source or changed_target))
