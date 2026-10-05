from evaluation.benchmarks.dev_inheritance import file_bindings


def test_git_serialization_rules_do_not_change_benchmark_artifact_bindings(tmp_path):
    (tmp_path/'source.json').write_text('{"source":"original"}\n',encoding='utf8')
    original=file_bindings(tmp_path)
    (tmp_path/'.gitattributes').write_text('* -text\n',encoding='utf8')
    (tmp_path/'.gitignore').write_text('cache/\n',encoding='utf8')
    assert file_bindings(tmp_path)==original
    (tmp_path/'source.json').write_text('{"source":"changed"}\n',encoding='utf8')
    assert file_bindings(tmp_path)!=original
