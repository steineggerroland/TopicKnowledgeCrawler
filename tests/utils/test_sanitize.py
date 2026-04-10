from crawler.utils.text_processor import sanitize_string


def test_sanitize_filename():
    """Test that filenames are sanitized correctly."""
    assert sanitize_string("My Source Name!") == "My_Source_Name_"
    assert sanitize_string("entry:id?") == "entry_id_"
    assert sanitize_string("valid_filename-123") == "valid_filename-123"
    assert sanitize_string("filename with spaces") == "filename_with_spaces"
    assert sanitize_string("äöüß") == "____"
