"""One-shot read-only source migration; refuses to replace destination files."""
import hashlib
import json
from pathlib import Path
import shutil

TARGET = Path(__file__).resolve().parent
SOURCE = TARGET.parent / 'NASA-Sandbox-etapa01'
EXCLUDE = {'.git', '__pycache__', '.pytest_cache', 'node_modules'}
records = []
for folder in ('prototypes/mission_planner', 'docs/continuidad', 'data/jezero', 'data/mission_planner_ctx_2km'):
    for source in sorted((SOURCE / folder).rglob('*')):
        rel = source.relative_to(SOURCE)
        if not source.is_file() or EXCLUDE.intersection(rel.parts) or source.suffix in ('.pyc', '.pyo'):
            continue
        destination = TARGET / rel
        if destination.exists():
            raise RuntimeError(f'Already exists: {rel}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copyfile(source, destination)
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        records.append(dict(path=rel.as_posix(), bytes=source.stat().st_size, sha256=digest))
output = TARGET / 'docs/migration'
output.mkdir(parents=True, exist_ok=True)
(output / 'source-manifest.json').write_text(json.dumps(dict(
    source='NASA-Sandbox-etapa01 local working tree; includes uncommitted stage 1-6 work',
    source_base_commit='0d5a444f5444b4dfa574224c9f7d09652dad1df5',
    sandbox_base_commit='471019a5377f2803612fcbac3ba5774310ec9d08',
    exclusions=sorted(EXCLUDE | {'.venv*', '*.pyc', '*.pyo'}), files=records), indent=2)+'\n', encoding='utf-8')
print(f'Copied and verified {len(records)} files, {sum(r["bytes"] for r in records)} bytes')
