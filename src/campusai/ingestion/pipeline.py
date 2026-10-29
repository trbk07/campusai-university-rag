"""Orchestrate validation, parsing, metadata detection, and persistence."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Callable

from ..schemas import Document
from .chunker import CHUNKER_VERSION, make_chunks
from .background.commit import atomic_text
from .docling_parser import TEXT_COVERAGE_VERSION, parse_pdf
from .metadata_detector import detect_metadata
from .ocr import OCRLimitExceeded, OCRUnavailable, ocr_pdf
from .table_extractor import TABLE_EXTRACTOR_VERSION, extract_tables
from .validate import ValidationError, validate_pdf
from ..documents.registry import DocumentRegistry


ProgressCallback = Callable[[str, float], None]


def _merge_hybrid_page(native, recognized):
    """Retain exact native text; add OCR lines only outside its known geometry."""
    import fitz
    layout = recognized.get('lines')
    audit = recognized.get('image_audit')
    if audit is not None:
        if not all(any(row.get('outcome') in {'recognized', 'no_detected_text'}
                       and fitz.Rect(row['bbox']).irect == fitz.Rect(region).irect
                       for row in audit) for region in native['ocr_regions']):
            return None
    if not layout and audit is None:
        return None  # A native header alone is not successful body recognition.
    originals = native['hybrid_layout']
    boxes = [fitz.Rect(row['bbox']) + (-2, -2, 2, 2) for row in originals]
    additions = []
    for row in layout or []:
        rect = fitz.Rect(row['bbox'])
        if not rect.get_area() or not row['text'].strip():
            continue
        if any((rect & box).get_area() >= .98 * rect.get_area() for box in boxes):
            continue
        normalized = ' '.join(row['text'].casefold().split())
        if any(' '.join(previous['text'].casefold().split()) == normalized
               and (rect & fitz.Rect(previous['bbox'])).get_area() >= .8 * min(
                   rect.get_area(), fitz.Rect(previous['bbox']).get_area()) for previous in additions):
            continue
        additions.append(row)
    if audit is None and not all(any((fitz.Rect(row['bbox']) & fitz.Rect(region)).get_area() > 0
                   for row in additions) for region in native['ocr_regions']):
        return None
    # Preserve each extractor's reading order. Sorting all lines by y/x would
    # interleave the left and right columns of a scanned body.
    insertions, remaining = {}, list(additions)
    for region in native['ocr_regions']:
        area = fitz.Rect(region)
        group = [row for row in remaining if area.contains(fitz.Rect(row['bbox']).tl
                  + (fitz.Rect(row['bbox']).br - fitz.Rect(row['bbox']).tl) * .5)]
        if not group:
            continue
        remaining = [row for row in remaining if row not in group]
        envelope = fitz.Rect()
        for row in group:
            envelope |= fitz.Rect(row['bbox'])
        preceding, following = [], []
        for index, row in enumerate(originals):
            box = fitz.Rect(row['bbox'])
            overlap = max(0, min(box.x1, envelope.x1) - max(box.x0, envelope.x0))
            if overlap < .3 * min(box.width, envelope.width):
                continue
            if box.y1 <= envelope.y0:
                preceding.append((box.y1, index))
            elif box.y0 >= envelope.y1:
                following.append((box.y0, index))
        position = max(preceding)[1] + 1 if preceding else min(following)[1] if following else len(originals)
        insertions.setdefault(position, []).extend(group)
    insertions.setdefault(len(originals), []).extend(remaining)
    ordered = []
    for index in range(len(originals) + 1):
        ordered.extend(insertions.get(index, []))
        if index < len(originals):
            ordered.append(originals[index])
    styles = {id(row): style for row, style in zip(originals, native.get('lines_meta', []))}
    # A native overlay inside a raster table needs separate mixed-source review;
    # do not publish duplicate/partly-native OCR tables as independently read cells.
    recognized={**recognized,'ocr_tables':[table for table in recognized.get('ocr_tables',[])
        if not any((fitz.Rect(table['bbox']) & fitz.Rect(row['bbox'])).get_area()>0 for row in originals)]}
    return {**recognized, 'text': '\n'.join(row['text'].strip() for row in ordered),
            'lines_meta': [styles.get(id(row), {'text': row['text'], 'is_larger_font': False})
                           for row in ordered]}


def _sha256_file(path: Path) -> str:
    """Return the content hash used as the stable document identifier."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _default_progress(_stage: str, _value: float) -> None:
    """Default callback used when the caller does not need progress updates."""


def _save_table(table, output_dir: Path) -> None:
    """Save a table when possible and always save its schema."""

    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd
    except ImportError:
        pd = None

    if pd is not None:
        dataframe = pd.DataFrame(table.rows, columns=table.headers)
        parquet_path = tables_dir / f"{table.table_id}.parquet"
        try:
            dataframe.to_parquet(parquet_path, index=False)
        except (ImportError, ValueError):
            # Parquet is optional; the JSON schema remains the durable output.
            pass

    schema_path = tables_dir / f"{table.table_id}.schema.json"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(schema_path,
        json.dumps(table.schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def ingest_document(
    path: str | Path,
    store_dir: str | Path = "data/store",
    max_mb: int = 50,
    max_pages: int = 218,
    progress: ProgressCallback | None = None,
    registry: DocumentRegistry | None = None,
    enable_ocr: bool = False,
    ocr_max_pages: int = 50,
    ocr_timeout_seconds: float = 120.0,
    ocr_backend: str = 'rapidocr',
    ocr_data_dir: str | Path | None = None,
) -> Document:
    """Ingest one PDF and reuse its stored result on repeated uploads."""

    pdf_path = Path(path)
    registry = registry or DocumentRegistry(Path(store_dir) / "registry.json")
    # Parsing below already reads every page. Deferring validation's text probe
    # avoids a complete second pass over the PDF on first ingestion.
    validation = validate_pdf(
        pdf_path,
        max_mb=max_mb,
        max_pages=max_pages,
        check_text=False,
    )
    document_id = _sha256_file(pdf_path)

    output_dir = Path(store_dir) / document_id
    metadata_path = output_dir / "meta.json"

    if metadata_path.exists():
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        document = Document.from_dict(data)
        parser_version = document.metadata.get("parser_version")
        cache_versions_current = (
            parser_version in {"pymupdf-text-v1", "rapidocr-onnx-v1", "tesseract-vie-eng-v1", "vietocr-vgg-seq2seq-v1"}
            and document.metadata.get("chunker_version") == CHUNKER_VERSION
            and document.metadata.get("table_extractor_version") == TABLE_EXTRACTOR_VERSION
            and document.metadata.get("text_coverage_version") == TEXT_COVERAGE_VERSION
        )
        cached_ocr = document.metadata.get('ocr')
        if (document.status == 'succeeded'
                and parser_version in {'rapidocr-onnx-v1', 'tesseract-vie-eng-v1', 'vietocr-vgg-seq2seq-v1'}
                and document.metadata.get('table_extractor_version') in {
                    'table-v4-physical-course-scope', 'table-v5-partial-numeric-grid', 'table-v6-leader-text-grid'}
                and document.metadata.get('chunker_version') == CHUNKER_VERSION
                and document.metadata.get('text_coverage_version') in {3, TEXT_COVERAGE_VERSION}
                and isinstance(cached_ocr, dict)
                and isinstance(cached_ocr.get('page_numbers'), list)
                and all(type(number) is int for number in cached_ocr['page_numbers'])
                and sorted(cached_ocr['page_numbers']) == list(range(1, document.page_count + 1))):
            # v5/v6/v7 only change native grids. Fully recognized pages
            # without visible native text cannot acquire such cells; preserve
            # completed OCR/chunks and record their actual previous producer.
            native_pages = parse_pdf(pdf_path)
            compatible = len(native_pages) == document.page_count and not any(
                str(page.get('text', '')).strip() or (page.get('untrusted_native_mapping')
                    and document.metadata.get('text_coverage_version') != TEXT_COVERAGE_VERSION)
                for page in native_pages)
            if compatible:
                document.metadata.setdefault('table_extractor_reused_from', document.metadata['table_extractor_version'])
                document.metadata['table_extractor_version'] = TABLE_EXTRACTOR_VERSION
                document.metadata['text_coverage_version'] = TEXT_COVERAGE_VERSION
                atomic_text(metadata_path, json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
                cache_versions_current = True
        if (document.metadata.get('text_coverage_version') in {2, 3}
                and parser_version in {'pymupdf-text-v1', 'rapidocr-onnx-v1', 'tesseract-vie-eng-v1', 'vietocr-vgg-seq2seq-v1'}
                and document.metadata.get('chunker_version') == CHUNKER_VERSION
                and document.metadata.get('table_extractor_version') == TABLE_EXTRACTOR_VERSION
                and not any(page.get('untrusted_native_mapping') or (
                    document.metadata.get('text_coverage_version') == 2
                    and page.get('ignored_invisible_spans')) for page in parse_pdf(pdf_path))):
            # Reuse unaffected v2/v3 content and chunks. A newly detected broken
            # font map requires fresh pixels even if older OCR covered an image.
            document.metadata['text_coverage_version'] = TEXT_COVERAGE_VERSION
            atomic_text(metadata_path, json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
            cache_versions_current = True
        if enable_ocr and cached_ocr and cached_ocr.get('backend', 'rapidocr') != ocr_backend:
            cache_versions_current = False
        if enable_ocr and ocr_backend=='vietocr' and cached_ocr:
            from .ocr_tables import OCR_TABLE_POLICY
            if document.metadata.get('ocr_table_policy')!=OCR_TABLE_POLICY:cache_versions_current=False
        if enable_ocr and ocr_backend in {'rapidocr','vietocr'} and cached_ocr:
            from .ocr_numeric_tables import NUMERIC_TABLE_POLICY
            if document.metadata.get('ocr_numeric_policy') != NUMERIC_TABLE_POLICY:
                cache_versions_current = False
        if enable_ocr and document.status == "review_required" and document.review_reason in {
            "ocr_required",
            "ocr_unavailable",
        }:
            # An earlier default ingestion may have persisted a fail-closed
            # scan review. Explicit OCR opt-in must be allowed to reprocess it.
            shutil.rmtree(output_dir, ignore_errors=True)
        elif cache_versions_current:
            document.cached = True
            registry.add(document)
            return document
        else:
            # A stable PDF hash does not imply that its parsed chunks remain
            # current after parser, chunker or table-extractor upgrades.
            shutil.rmtree(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_progress = progress or _default_progress
    report_progress("validating", 1.0)
    report_progress("parsing", 0.0)

    pages = parse_pdf(
        pdf_path,
        progress=lambda value: report_progress("parsing", value),
    )
    report_progress("parsing", 1.0)
    ocr_info = None
    untrusted_pages = [int(page['page']) for page in pages if page.get('untrusted_native_mapping')]
    unread_pages = [int(page['page']) for page in pages if page.get('requires_ocr')]
    if not unread_pages and not any(str(page.get('text', '')).strip() for page in pages):
        unread_pages = [int(page['page']) for page in pages]
    review_reason, review_warning = 'ocr_required', None
    if unread_pages and enable_ocr:
        report_progress('ocr', 0.0)
        try:
            ocr_result = ocr_pdf(pdf_path, max_pages=ocr_max_pages,
                timeout_seconds=ocr_timeout_seconds, page_numbers=unread_pages,
                progress=lambda completed,total:report_progress('ocr',completed/total),
                backend=ocr_backend, data_dir=ocr_data_dir,
                include_layout=any(page.get('hybrid_layout') for page in pages),
                hybrid_regions={page['page']: page['ocr_regions'] for page in pages if page.get('hybrid_layout')})
            recognized = {page['page']: page for page in ocr_result.pages
                          if page.get('page') in unread_pages and (str(page.get('text', '')).strip()
                              or page.get('image_audit'))}
            for page in pages:
                if page.get('hybrid_layout') and page['page'] in recognized:
                    merged = _merge_hybrid_page(page, recognized[page['page']])
                    if merged is None:
                        del recognized[page['page']]
                    else:
                        recognized[page['page']] = merged
            pages = [{**recognized[page['page']], 'lines_meta': recognized[page['page']].get('lines_meta', []), 'requires_ocr': False,
                      **({key:page[key] for key in ('ignored_invisible_spans','visible_characters','untrusted_native_mapping')
                         if key in page} if page.get('ignored_invisible_spans')
                            or page.get('untrusted_native_mapping') else {})}
                     if page['page'] in recognized else page for page in pages]
            ocr_info = {'engine': ocr_result.engine, 'average_confidence': ocr_result.average_confidence,
                'elapsed_seconds': ocr_result.elapsed_seconds, 'pages': len(recognized),
                'page_numbers': sorted(recognized), 'backend': ocr_backend,
                'model_identity': ocr_result.model_identity}
            image_audits = [{'page': page['page'], 'regions': page['image_audit']}
                            for page in ocr_result.pages if page.get('image_audit')]
            if image_audits:
                ocr_info['image_audits'] = image_audits
            unread_pages = [number for number in unread_pages if number not in recognized]
            report_progress('ocr', 1.0)
        except (OCRLimitExceeded, OCRUnavailable) as error:
            review_reason, review_warning = 'ocr_unavailable', str(error)
    if unread_pages:
        metadata = detect_metadata('')
        warnings = ['unread_pages', review_reason]
        if not any(str(page.get('text', '')).strip() for page in pages):
            warnings.append('no_extractable_text')
        if review_warning:
            warnings.append(review_warning)
        metadata.update({'source_name': pdf_path.name, 'source_hash': document_id,
            'parser_version': 'pymupdf-text-v1', 'chunker_version': CHUNKER_VERSION,
            'table_extractor_version': TABLE_EXTRACTOR_VERSION, 'text_coverage_version': TEXT_COVERAGE_VERSION,
            **({'untrusted_native_pages': untrusted_pages} if untrusted_pages else {}),
            'schema_version': 1, 'status': 'review_required', 'review_reason': review_reason,
            'warnings': warnings, 'unread_pages': unread_pages})
        if ocr_info is not None:
            metadata['ocr'] = ocr_info
        document = Document(doc_id=document_id, source_path=str(pdf_path.resolve()),
            page_count=validation.pages, language=None, metadata=metadata, chunks=[], tables=[],
            status='review_required', review_reason=review_reason)
        atomic_text(metadata_path, json.dumps(document.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        registry.add(document)
        report_progress('review_required', 1.0)
        return document
    full_text = "\n\n".join(
        f"## Page {page['page']}\n{page['text']}" for page in pages
    )
    report_progress("detecting_metadata", 0.0)
    metadata = detect_metadata(full_text)
    metadata["source_name"] = pdf_path.name
    metadata["source_hash"] = document_id
    metadata["parser_version"] = "pymupdf-text-v1"
    metadata["chunker_version"] = CHUNKER_VERSION
    metadata["table_extractor_version"] = TABLE_EXTRACTOR_VERSION
    metadata["schema_version"] = 1
    metadata["text_coverage_version"] = TEXT_COVERAGE_VERSION
    if untrusted_pages:
        metadata['untrusted_native_pages'] = untrusted_pages
    if ocr_info is not None:
        metadata["ocr"] = ocr_info
        metadata["parser_version"] = ({'tesseract':'tesseract-vie-eng-v1',
            'vietocr':'vietocr-vgg-seq2seq-v1'}.get(ocr_backend,'rapidocr-onnx-v1'))
        metadata["warnings"] = ["ocr_used"]
        if ocr_backend=='vietocr':
            from .ocr_tables import OCR_TABLE_POLICY
            metadata['ocr_table_policy']=OCR_TABLE_POLICY
        if ocr_backend in {'rapidocr','vietocr'}:
            from .ocr_numeric_tables import NUMERIC_TABLE_POLICY
            metadata['ocr_numeric_policy']=NUMERIC_TABLE_POLICY
    report_progress("detecting_metadata", 1.0)
    report_progress("extracting_tables", 0.0)
    tables = extract_tables(pages, document_id, pdf_path=pdf_path)
    for table in tables:
        table.schema.update(
            {
                "domain": metadata.get("domain", "general"),
                "document_type": metadata.get("document_type", "unknown"),
                "academic_years": metadata.get("academic_years", []),
                "years": metadata.get("years", []),
                "semesters": metadata.get("semesters", []),
                "language": metadata.get("language"),
                "units": metadata.get("units", []),
                "currency": metadata.get("currency"),
            }
        )
    report_progress("extracting_tables", 1.0)
    report_progress("chunking", 0.0)
    chunk_diagnostics: dict = {}
    chunks = make_chunks(pages, document_id, metadata, tables, diagnostics=chunk_diagnostics)
    metadata["chunk_diagnostics"] = chunk_diagnostics
    metadata["warnings"] = list(dict.fromkeys([*metadata.get("warnings", []), *validation.warnings]))
    report_progress("chunking", 1.0)

    document = Document(
        doc_id=document_id,
        source_path=str(pdf_path.resolve()),
        page_count=validation.pages,
        language=metadata.get("language"),
        metadata=metadata,
        chunks=chunks,
        tables=tables,
        status="succeeded",
    )

    report_progress("persisting", 0.0)
    parsed_path = output_dir / "parsed.md"
    atomic_text(parsed_path,full_text, encoding="utf-8")

    for table in tables:
        _save_table(table, output_dir)

    atomic_text(metadata_path,
        json.dumps(document.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_progress("persisting", 1.0)

    registry.add(document)

    report_progress("done", 1.0)
    return document


def delete_document(
    doc_id: str,
    *,
    store_dir: str | Path = "data/store",
    registry: DocumentRegistry | None = None,
) -> bool:
    """Delete every persisted artifact for a document idempotently.

    ``doc_id`` is a SHA-256 identifier, so accepting any other shape would make
    path construction needlessly risky. Index/cache backends can additionally
    remove their own records before or after this storage-level operation.
    """

    if not re.fullmatch(r"[0-9a-f]{64}", str(doc_id)):
        raise ValueError("doc_id phải là SHA-256 hex")
    root = Path(store_dir).resolve()
    registry = registry or DocumentRegistry(root / "registry.json")
    removed = registry.remove(doc_id)
    artifact_dir = (root / doc_id).resolve()
    try:
        artifact_dir.relative_to(root)
    except ValueError as error:
        raise ValueError("artifact path nằm ngoài store root") from error
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    return removed is not None or not artifact_dir.exists()


def delete_document_full(
    doc_id: str,
    *,
    store_dir: str | Path = "data/store",
    index_dir: str | Path | None = None,
    llm_cache=None,
    registry: DocumentRegistry | None = None,
) -> dict[str, bool]:
    """Delete storage artifacts and any per-document retrieval artifacts."""
    result = {"store": delete_document(doc_id, store_dir=store_dir, registry=registry)}
    if index_dir is not None:
        from ..retrieval.index_builder import remove_document_from_index

        result["index"] = remove_document_from_index(doc_id, index_dir)
    if llm_cache is not None:
        # LLM cache keys are provider/query hashes and intentionally contain no
        # doc_id, so there is no safe document-scoped purge operation.
        result["cache"] = bool(getattr(llm_cache, "purge_by_doc_id", lambda _doc_id: False)(doc_id))
    return result
