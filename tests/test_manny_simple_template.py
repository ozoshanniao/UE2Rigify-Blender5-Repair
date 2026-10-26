"""Validate the independent template and its packaged resources without Blender."""
import ast
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'ue2rigify'
BASE = ADDON / 'resources/rig_templates/b4_0/male_mannequin_UE5'
SIMPLE = BASE.parent / 'male_manny_simple_ue5'

def normalized(data):
    # Git may check text resources out as LF or CRLF. ZIP bytes stay unchanged.
    return data.replace(b'\r\n', b'\n')


metadata = json.loads((SIMPLE / 'template_info.json').read_text(encoding='utf-8'))
assert metadata['based_on'] == BASE.name
assert len(metadata['corrective_root_fallbacks']) == 8
assert normalized((SIMPLE / 'metarig.py').read_bytes()) == normalized((BASE / 'metarig.py').read_bytes())
for path in BASE.iterdir():
    if path.is_file():
        content = normalized(path.read_bytes())
        candidates = (content, content.replace(b'\n', b'\r\n'))
        assert metadata['original_template_sha256'][path.name] in {hashlib.sha256(value).hexdigest() for value in candidates}

for mode, source_key in [('fk_to_source', 'to_socket'), ('source_to_deform', 'from_socket')]:
    links = json.loads((SIMPLE / f'{mode}_links.json').read_text())
    base_links = json.loads((BASE / f'{mode}_links.json').read_text())
    nodes = {node['name']: node for node in json.loads((SIMPLE / f'{mode}_nodes.json').read_text())}
    for link in links:
        assert link['from_socket'] in nodes[link['from_node']]['outputs'], link
        assert link['to_socket'] in nodes[link['to_node']]['inputs'], link
        assert link[source_key] not in metadata['omitted_source_bones']
        assert link[source_key] not in metadata['corrective_root_fallbacks']
    expected_twists = [link for link in base_links if '_twist_' in link[source_key]]
    assert expected_twists and all(link in links for link in expected_twists)
    if mode == 'fk_to_source':
        for missing, main in metadata['corrective_root_fallbacks'].items():
            original = next(link for link in base_links if link[source_key] == missing)
            assert any(link[source_key] == main and link['from_socket'] == original['from_socket'] for link in links)

module = ast.parse((ADDON / '__init__.py').read_text(encoding='utf-8'))
info = next(ast.literal_eval(node.value) for node in module.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'bl_info' for target in node.targets))
version = '.'.join(map(str, info['version']))
with ZipFile(ROOT / 'dist' / f'ue2rigify_{version}_blender5_repaired.zip') as archive:
    assert archive.testzip() is None
    for directory in (BASE, SIMPLE):
        for path in directory.iterdir():
            if path.is_file() and path.suffix != '.pyc':
                assert normalized(archive.read(path.relative_to(ROOT).as_posix())) == normalized(path.read_bytes())
with ZipFile(ROOT / 'dist/male_manny_simple_ue5.zip') as archive:
    assert archive.testzip() is None
    assert 'metarig.py' in archive.namelist()  # Import Template expects files at ZIP root.
    for path in SIMPLE.iterdir():
        if path.is_file():
            assert normalized(archive.read(path.name)) == normalized(path.read_bytes())
print('MANNY_SIMPLE_TEMPLATE_PACKAGE_PASS', version)
