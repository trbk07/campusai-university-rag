"""Optional source-owned relation index. No gold, model, or inferred edges."""
from __future__ import annotations

from collections import defaultdict, OrderedDict
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from threading import RLock

from .context import authorized_scope
from .course_credits import course_code_key, course_name_key, folded, headed_credit_rows
from .multi_hop import CODE
from .multi_hop_evidence import Premise, table, prerequisite, prerequisite_claim_support
from ..retrieval.tokenizer_vi import source_body
import re
from ..retrieval.contracts import FILTER_FIELDS, validate_filters
from ..retrieval.hybrid import RetrievalResult

POLICY_VERSION = 'source-relations-v1'
PREREQUISITE_HEADERS = {'ma so hoc phan tien quyet', 'ma hoc phan tien quyet',
                        'hoc phan tien quyet', 'prerequisite', 'prerequisites', 'prerequisite code'}


class RelationUnavailable(ValueError):
    """A derived index cannot prove this request; never a successful answer."""


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def extractor_fingerprint():
    return _digest(b''.join(Path(p).read_bytes() for p in [__file__,
        Path(__file__).with_name('course_credits.py'), Path(__file__).with_name('multi_hop_evidence.py')]))


def extract_nodes(doc_id, items):
    """Preserve source coordinates; ambiguity is retained rather than pruned."""
    variants = defaultdict(list)
    for item in items:
        value = table(item.get('content', ''))
        if not value:
            continue
        headers = value['headers']
        relation_cols = [i for i, h in enumerate(headers) if folded(h) in PREREQUISITE_HEADERS]
        name_cols = [i for i, h in enumerate(headers) if folded(h) in {
            'hoc phan', 'ten hoc phan', 'course name', 'discipline'} or folded(h).startswith('hoc phan (')]
        for code, credit, cells in headed_credit_rows(item['content']) or []:
            raw = cells[relation_cols[0]] if len(relation_cols) == 1 and len(cells) > relation_cols[0] else None
            raw = raw.strip() if isinstance(raw,str) else raw
            name = cells[name_cols[0]] if len(name_cols) == 1 and len(cells) > name_cols[0] else None
            metadata = item.get('metadata', {})
            proof = dict(doc_id=doc_id, chunk_id=item['chunk_id'], page=item['page'],
                row_index=value['rows'].index(cells), headers=headers, cells=cells,
                row_sha256=_digest(_json(cells).encode()), metadata={k:v for k,v in metadata.items() if k in FILTER_FIELDS | {
                    'source_hash','source_name','page_range','table_id','heading_path','version'}},
                source_hash=metadata.get('source_hash'), relation_column=relation_cols[0] if len(relation_cols) == 1 else None)
            scope = (str(metadata.get('program', '')), str(metadata.get('version', '')))
            variants[code].append(dict(code=code, credit=credit, name=name, raw=raw, proof=proof, scope=scope))
    nodes, blocked = {}, set()
    for code, records in variants.items():
        def signature(record):
            raw = record['raw']
            relation = course_code_key(raw) if isinstance(raw, str) and CODE.fullmatch(raw.strip()) else raw
            return (record['credit'], course_name_key(record['name'] or ''), relation, record['scope'])
        first = records[0]
        status = 'ready' if len({signature(r) for r in records}) == 1 else 'conflict'
        raw = first['raw']
        single = isinstance(raw, str) and CODE.fullmatch(raw.strip())
        relation = 'single' if single else ('blank' if raw == '' else 'unsupported')
        requires = course_code_key(raw) if single else None
        if status == 'conflict' or relation == 'unsupported':
            for record in records:
                codes = {course_code_key(m[1]) for m in CODE.finditer(record['raw'] or '')}
                if record['raw'] != '':
                    blocked.update(codes or {'*'})
        nodes[code] = dict(**first, status=status, relation=relation, requires=requires)
    # Reuse the exact standalone-statement verifier; endpoint co-occurrence
    # never creates an edge. Both endpoint identities still need headed rows.
    statements = defaultdict(list)
    for item in items:
        if table(item.get('content', '')):
            continue
        result = RetrievalResult(item['chunk_id'], doc_id, item['page'], item['content'],
            item.get('content_type','text'),1.0,'source_relations',item.get('metadata',{}))
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', source_body(item,decode_tables=False)):
            codes = [course_code_key(m[1]) for m in CODE.finditer(sentence)]
            if len(codes)==2 and prerequisite_claim_support(sentence,[result]) == (True,(item['chunk_id'],)):
                statements[codes[1]].append((codes[0],dict(chunk_id=item['chunk_id'],page=item['page'],quote=sentence,
                    metadata=item.get('metadata',{}))))
    for dependent, values in statements.items():
        node = nodes.get(dependent)
        targets = {code for code,proof in values}
        if not node or len(targets)!=1 or node['status']!='ready' or node['relation']=='unsupported':
            blocked.update(targets)
            if node:
                node['status']='conflict'
            continue
        target, proof = values[0]
        if node['requires'] and node['requires'] != target:
            node['status']='conflict';blocked.update([target,node['requires']])
        elif not node['requires']:
            node.update(requires=target,relation='single',statement_proof=proof)
    edges = []
    for code, node in nodes.items():
        child = nodes.get(node['requires'])
        if node['status'] == 'ready' and node['relation'] == 'single':
            if child and child['status'] == 'ready' and child['code'] != code:
                edges.append((code, child['code']))
            else:
                blocked.add(node['requires'])
    return nodes, edges, blocked


class RelationIndex:
    """One SQLite sidecar; sources remain authoritative and scope comes first."""

    def __init__(self, index_root, path=None):
        self.index_root = Path(index_root).resolve()
        self.path = Path(path) if path is not None else self.index_root / 'relations.sqlite3'
        self.manifest_path = self.path.with_suffix('.manifest.json')
        self._lock = RLock()
        self._hashes, self._sources = OrderedDict(), OrderedDict()

    def _hash(self, path):
        try:
            stat = path.stat()
        except OSError as exc:
            raise RelationUnavailable('relation_source_missing') from exc
        generation = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        old = self._hashes.get(path)
        if not old or old[0] != generation:
            old = (generation, _digest(path.read_bytes()))
            self._hashes[path] = old
        self._hashes.move_to_end(path)
        while len(self._hashes) > 256:
            self._hashes.popitem(last=False)
        return old[1]

    def _source_signature(self, doc_id):
        authorized_scope([doc_id], [doc_id])
        base = self.index_root / doc_id
        return {name: self._hash(base / name) if (base / name).is_file() else None
                for name in ['bm25.json', 'dense.json']}

    def _source(self, doc_id, trace=None):
        signature = self._source_signature(doc_id)
        if not signature['bm25.json']:
            raise RelationUnavailable('relation_source_missing')
        old = self._sources.get(doc_id)
        if not old or old[0] != signature['bm25.json']:
            data = json.loads((self.index_root / doc_id / 'bm25.json').read_text(encoding='utf-8-sig'))
            items = data['items']
            if any(i.get('doc_id', doc_id) != doc_id for i in items):
                raise RelationUnavailable('relation_source_identity_mismatch')
            by_id = {i['chunk_id']: i for i in items}
            if len(by_id) != len(items):
                raise RelationUnavailable('relation_source_duplicate_chunk')
            old = (signature['bm25.json'], by_id)
            self._sources[doc_id] = old
            if trace is not None:
                trace['cold_source_loads'] += 1
        self._sources.move_to_end(doc_id)
        while len(self._sources) > 8:
            self._sources.popitem(last=False)
        return old[1]

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    def _manifest(self):
        manifest = json.loads(self.manifest_path.read_text(encoding='utf-8'))
        if manifest.get('policy') != POLICY_VERSION or manifest.get('extractor') != extractor_fingerprint():
            raise RelationUnavailable('relation_policy_stale')
        if manifest.get('db_sha256') != self._hash(self.path):
            raise RelationUnavailable('relation_index_corrupt')
        return manifest

    def fingerprint(self, doc_ids):
        """Validate selected sources before cache reuse, never traverse others."""
        with self._lock:
            try:
                manifest = self._manifest()
                for doc in authorized_scope(doc_ids, doc_ids):
                    if manifest['sources'].get(doc) != self._source_signature(doc):
                        raise RelationUnavailable('relation_source_stale')
                return _digest(_json(manifest).encode())
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                raise RelationUnavailable(str(exc)) from exc

    def rebuild(self, doc_ids=None):
        """Offline/job operation; two-file publication fails closed on interruption."""
        with self._lock:
            if doc_ids is None:
                doc_ids = sorted(p.name for p in self.index_root.iterdir()
                                 if p.is_dir() and (p / 'bm25.json').is_file())
            doc_ids = authorized_scope(doc_ids, doc_ids)
            signatures = {doc: self._source_signature(doc) for doc in doc_ids}
            extractor = extractor_fingerprint()
            try:
                old = self._manifest()
                if old['sources'] == signatures:
                    return dict(old, rebuilt=False)
            except (OSError, ValueError, KeyError):
                pass
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.relation-build-', suffix='.sqlite3', dir=self.path.parent)
            os.close(fd)
            temporary = Path(temporary)
            meta_temp = temporary.with_suffix('.manifest.json')
            counts = {}
            connection = None
            try:
                connection = sqlite3.connect(temporary)
                connection.executescript('''
                    CREATE TABLE nodes(doc TEXT, code TEXT, data TEXT NOT NULL, filters TEXT NOT NULL, PRIMARY KEY(doc,code));
                    CREATE TABLE edges(doc TEXT, dependent TEXT, prerequisite TEXT, filters TEXT NOT NULL, PRIMARY KEY(doc,dependent,prerequisite));
                    CREATE INDEX reverse_edges ON edges(doc,prerequisite,dependent);
                    CREATE TABLE blocked(doc TEXT, code TEXT, PRIMARY KEY(doc,code));
                ''')
                for doc in doc_ids:
                    nodes, edges, blocked = extract_nodes(doc, list(self._source(doc).values()))
                    connection.executemany('INSERT INTO nodes VALUES (?,?,?,?)',
                        [(doc, code, _json(node), _json({k: str(v).casefold() for k,v in node['proof']['metadata'].items() if k in FILTER_FIELDS})) for code,node in nodes.items()])
                    connection.executemany('INSERT INTO edges VALUES (?,?,?,?)',
                        [(doc,a,b,_json({k:str(v).casefold() for k,v in
                            nodes[a].get('statement_proof',nodes[a]['proof'])['metadata'].items() if k in FILTER_FIELDS})) for a,b in edges])
                    connection.executemany('INSERT INTO blocked VALUES (?,?)', [(doc,c) for c in sorted(blocked)])
                    counts[doc] = dict(nodes=len(nodes), edges=len(edges), conflicts=sum(n['status']=='conflict' for n in nodes.values()),
                        unsupported=sum(n['relation']=='unsupported' for n in nodes.values()))
                connection.commit()
                connection.close()
                connection = None
                if {doc: self._source_signature(doc) for doc in doc_ids} != signatures:
                    raise RelationUnavailable('source_changed_during_relation_build')
                manifest = dict(policy=POLICY_VERSION, extractor=extractor, sources=signatures, counts=counts,
                                db_sha256=_digest(temporary.read_bytes()))
                meta_temp.write_text(_json(manifest)+'\n', encoding='utf-8')
                os.replace(temporary, self.path)
                os.replace(meta_temp, self.manifest_path)
                return dict(manifest, rebuilt=True)
            finally:
                if connection is not None:
                    connection.close()
                temporary.unlink(missing_ok=True)
                meta_temp.unlink(missing_ok=True)

    def lookup(self, doc_id, code, *, kind='direct', filters=None):
        """Return proved rows/edges, with no search, encoder, or generation."""
        trace = dict(kind=kind, doc_id=doc_id, adjacency_lookups=0, nodes_visited=0, edges_visited=0,
                     proof_fetches=0, cold_source_loads=0, candidate_chunks=0, problem=None)
        premises, edges, seen, edge_evidence = {}, [], set(), {}
        with self._lock:
            try:
                if kind not in {'direct','inverse','chain2'}:
                    raise RelationUnavailable('unsupported_relation_query')
                expected_fingerprint = self.fingerprint([doc_id])
                normalized = validate_filters(filters)
                clauses = ''.join(f" AND json_extract(n.filters,'$.{k}')=?" for k in normalized)
                parameters = [str(v).casefold() for v in normalized.values()]
                with self._connect() as connection:
                    def node(key):
                        if key in premises:
                            return premises[key]
                        if len(premises) >= 40:
                            raise RelationUnavailable('relation_node_budget_exceeded')
                        record = connection.execute('SELECT n.data FROM nodes n WHERE n.doc=? AND n.code=?'+clauses,
                                                    [doc_id,key,*parameters]).fetchone()
                        if not record:
                            raise RelationUnavailable('missing_or_filtered_relation_node')
                        data = json.loads(record['data'])
                        if data['status'] != 'ready':
                            raise RelationUnavailable('conflicting_relation_node')
                        proof = data['proof']
                        item = self._source(doc_id, trace).get(proof['chunk_id'])
                        if item is None:
                            raise RelationUnavailable('dangling_relation_proof')
                        value = table(item['content'])
                        if (not value or item['page'] != proof['page'] or value['headers'] != proof['headers']
                                or value['rows'][proof['row_index']] != proof['cells']
                                or _digest(_json(proof['cells']).encode()) != proof['row_sha256']
                                or any(str(item.get('metadata',{}).get(k,'')).casefold()!=str(v).casefold() for k,v in normalized.items())
                                or not any(c==key and r==proof['cells'] and credit==data['credit']
                                           for c,credit,r in headed_credit_rows(item['content']) or [])):
                            raise RelationUnavailable('relation_proof_changed')
                        result = RetrievalResult(item['chunk_id'], doc_id, item['page'], item['content'],
                            item.get('content_type','table'), 1.0, 'source_relations', item.get('metadata',{}))
                        premise = Premise(result, tuple(proof['headers']), tuple(proof['cells']), proof['row_index'], key, data['credit'])
                        premises[key] = dict(data=data, premise=premise)
                        trace.update(nodes_visited=len(premises), proof_fetches=trace['proof_fetches']+1,
                                     candidate_chunks=len({p['premise'].result.chunk_id for p in premises.values()}))
                        return premises[key]
                    current = course_code_key(code)
                    node(current)
                    for _ in range(2 if kind=='chain2' else 1):
                        trace['adjacency_lookups'] += 1
                        if kind == 'inverse':
                            if connection.execute('SELECT COUNT(*) FROM blocked WHERE doc=? AND code IN (?,?)',
                                                  (doc_id,current,'*')).fetchone()[0]:
                                raise RelationUnavailable('inverse_relation_incomplete')
                            endpoint = 'prerequisite'
                        else:
                            endpoint = 'dependent'
                        query = ('SELECT e.dependent,e.prerequisite FROM edges e '
                                 'JOIN nodes n ON n.doc=e.doc AND n.code=e.dependent '
                                 'JOIN nodes m ON m.doc=e.doc AND m.code=e.prerequisite '
                                 'WHERE e.doc=? AND e.'+endpoint+'=?'+clauses+clauses.replace('n.filters','m.filters')+clauses.replace('n.filters','e.filters'))
                        query_parameters = [doc_id,current,*parameters,*parameters,*parameters]
                        count = connection.execute('SELECT COUNT(*) FROM ('+query+')', query_parameters).fetchone()[0]
                        if count > 40-len(premises) or count > 40-len(edges):
                            raise RelationUnavailable('relation_fanout_budget_exceeded')
                        rows = connection.execute(query+' ORDER BY e.dependent,e.prerequisite', query_parameters).fetchall()
                        if not rows or kind != 'inverse' and len(rows) != 1:
                            raise RelationUnavailable('direct_edge_not_established')
                        seen.add(current)
                        for row in rows:
                            parent, child = node(row['dependent']), node(row['prerequisite'])
                            if parent['data']['requires'] != row['prerequisite']:
                                raise RelationUnavailable('relation_direction_or_edge_mismatch')
                            statement = parent['data'].get('statement_proof')
                            if statement:
                                item = self._source(doc_id,trace).get(statement['chunk_id'])
                                if (item is None or item['page'] != statement['page'] or
                                        any(str(item.get('metadata',{}).get(k,'')).casefold()!=str(v).casefold() for k,v in normalized.items())):
                                    raise RelationUnavailable('dangling_relation_statement')
                                evidence = RetrievalResult(item['chunk_id'],doc_id,item['page'],item['content'],
                                    item.get('content_type','text'),1.0,'source_relations',item.get('metadata',{}))
                                codes = [course_code_key(m[1]) for m in CODE.finditer(statement['quote'])]
                                if (codes != [row['prerequisite'],row['dependent']] or
                                    prerequisite_claim_support(statement['quote'],[evidence]) != (True,(evidence.chunk_id,))):
                                    raise RelationUnavailable('relation_statement_not_proved')
                                edge_evidence[(row['dependent'],row['prerequisite'])] = dict(result=evidence,quote=statement['quote'])
                                trace['proof_fetches'] += 1
                            elif prerequisite(parent['premise']) != row['prerequisite']:
                                raise RelationUnavailable('relation_source_edge_not_proved')
                            next_code = row['dependent'] if kind=='inverse' else row['prerequisite']
                            if next_code in seen:
                                raise RelationUnavailable('relation_cycle')
                            edges.append((parent['premise'],child['premise']))
                            trace['edges_visited'] = len(edges)
                            current = next_code
                if self.fingerprint([doc_id]) != expected_fingerprint:
                    raise RelationUnavailable('relation_generation_changed')
                trace['candidate_chunks'] = len({p['premise'].result.chunk_id for p in premises.values()} |
                    {e['result'].chunk_id for e in edge_evidence.values()})
                if trace['candidate_chunks'] > 40:
                    raise RelationUnavailable('relation_candidate_budget_exceeded')
                return dict(trace=trace, edges=edges, premises=[v['premise'] for v in premises.values()],
                            final=next(reversed(premises.values()))['premise'], nodes={k:v['data'] for k,v in premises.items()},edge_evidence=edge_evidence)
            except (OSError, ValueError, KeyError, TypeError, IndexError, sqlite3.Error) as exc:
                trace['problem'] = str(exc)
                return dict(trace=trace, edges=[], premises=[], final=None, nodes={},edge_evidence={})
