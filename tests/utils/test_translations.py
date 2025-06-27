from markitdowngui.utils.translations import get_translation, get_available_languages, TRANSLATIONS

def test_get_translation_english():
    """Test retrieving a standard English translation."""
    assert get_translation('en', 'app_title') == "MarkItDown GUI Wrapper"

def test_get_translation_chinese():
    """Test retrieving a standard Chinese translation."""
    assert get_translation('zh_CN', 'app_title') == "MarkItDown GUI 包装器"

def test_get_translation_fallback_to_english():
    """Test that it falls back to English if a key is missing in another language."""
    # Temporarily add a key that only exists in English
    TRANSLATIONS['en']['only_in_english'] = 'English Fallback'
    assert get_translation('zh_CN', 'only_in_english') == 'English Fallback'
    del TRANSLATIONS['en']['only_in_english'] # Clean up the temporary key

def test_get_translation_fallback_to_key():
    """Test that it falls back to the key itself if no translation is found."""
    assert get_translation('en', 'a_completely_nonexistent_key') == 'a_completely_nonexistent_key'

def test_get_translation_nonexistent_language():
    """Test that it falls back to English for a language that doesn't exist."""
    assert get_translation('de', 'app_title') == "MarkItDown GUI Wrapper"

def test_get_available_languages():
    """Test that it returns the correct dictionary of available languages."""
    langs = get_available_languages()
    assert 'en' in langs
    assert 'zh_CN' in langs
    assert langs['en'] == "&English"
    assert langs['zh_CN'] == "简体中文(&S)" 