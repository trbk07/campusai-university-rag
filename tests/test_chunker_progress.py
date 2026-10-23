"""A page-ending heading must not stall an ingestion worker forever."""
import json
import subprocess
import sys

import pytest


@pytest.mark.parametrize('continuation', [
    'This sentence is ordinary prose.',
    'use the next section for details',
])
def test_heading_followed_by_non_title_always_makes_progress(continuation):
    pages = [{'page':1, 'text':'1 Introduction'}, {'page':2, 'text':continuation}]
    code = ('import json; from campusai.ingestion.chunker import _sectionize; '
            f'print(json.dumps(_sectionize({pages!r})))')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            check=True, timeout=5)
    sections, _ = json.loads(result.stdout.splitlines()[-1])
    text = '\n'.join(section[0] for section in sections)
    assert '1 Introduction' in text and continuation in text
    assert sections[0][2:] == [1, 2]
