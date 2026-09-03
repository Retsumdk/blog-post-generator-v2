from blog_post_generator_v2 import digest, normalize, run

def test_normalize_deterministic():
    assert normalize({'b': 1, 'a': 2}) == normalize({'a': 2, 'b': 1})

def test_digest_stable():
    assert digest('x') == digest('x')
    assert digest({'k': 'v'}) == digest({'k': 'v'})

def test_run_shapes_result():
    out = run({'hello': 'world'})
    assert out['input_type'] == 'dict'
    assert out['length'] > 0
    assert len(out['digest']) == 64
