from backend.main import is_valid_fixed_code


def test_valid_fixed_code_accepts_markdown_python_block():
    code = '''Here is the corrected version:\n```python\nprint("hello")\n```'''
    assert is_valid_fixed_code(code, "Python") is True


def test_valid_fixed_code_accepts_plain_python_code():
    code = 'def greet():\n    print("hello")\n\ngreet()\n'
    assert is_valid_fixed_code(code, "Python") is True
