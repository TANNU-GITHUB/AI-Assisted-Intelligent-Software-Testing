from pathlib import Path

from code_analysis.analyzer import analyze_source


SAMPLE = Path("examples/sample_source.py").read_text(encoding="utf-8")


def test_extracts_functions_and_complexity():
    result = analyze_source(SAMPLE)
    by_name = {fn["name"]: fn for fn in result["functions"]}

    discount = by_name["calculate_discount"]
    assert [p["name"] for p in discount["params"]] == ["price", "is_member"]
    assert discount["return_type"] == "float"
    assert discount["branch_count"] == 2
    assert discount["cyclomatic_complexity"] == 3

    checkout = by_name["checkout_total"]
    assert checkout["branch_count"] == 2  # for-loop + if
    assert checkout["cyclomatic_complexity"] >= 3


def test_class_methods_are_qualified():
    source = '''
class Cart:
    def total(self, items):
        if not items:
            return 0
        return sum(items)
'''
    result = analyze_source(source)
    assert result["functions"][0]["qualified_name"] == "Cart.total"
    assert result["functions"][0]["cyclomatic_complexity"] == 2
