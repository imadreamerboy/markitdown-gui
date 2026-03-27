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

def test_home_translation_keys_exist():
    """Ensure new Home UX translation keys exist in both languages."""
    required_keys = [
        "home_empty_state_title",
        "home_queue_title_with_count",
        "home_back_to_queue_button",
        "home_start_over_button",
        "home_rendered_view_button",
        "home_raw_view_button",
        "home_copy_markdown_button",
        "home_save_markdown_button",
        "home_add_url_button",
        "home_url_placeholder",
        "home_url_invalid_title",
        "home_url_invalid_message",
        "home_preview_file_default",
        "home_preview_for_file",
        "home_save_mode_label",
        "home_save_mode_combined",
        "home_save_mode_separate",
        "remove_selected_action",
        "clear_list_action",
        "settings_ocr_group",
        "settings_ocr_enable_label",
        "settings_docintel_label",
        "settings_test_azure_button",
        "settings_test_azure_in_progress",
        "settings_test_azure_tooltip",
        "settings_test_azure_success_title",
        "settings_test_azure_success_message",
        "settings_test_azure_failure_title",
        "settings_test_azure_failure_message",
        "settings_test_azure_auth_api_key",
        "settings_test_azure_auth_identity",
        "settings_ocr_language_label",
        "settings_tesseract_path_label",
        "settings_tesseract_dialog",
        "conversion_partial_failure_title",
        "conversion_partial_failure_message",
        "conversion_backend_summary",
        "conversion_backend_summary_item",
        "conversion_backend_azure",
        "conversion_backend_defuddle",
        "conversion_backend_local",
        "conversion_backend_native",
        "conversion_source_heading",
        "help_open_defuddle_docs",
        "help_open_azure_ocr_pricing",
        "help_open_tesseract",
        "help_faq_title",
        "help_faq_defuddle_question",
        "help_faq_defuddle_answer",
        "help_faq_defuddle_limits_question",
        "help_faq_defuddle_limits_answer",
        "help_faq_tesseract_windows_question",
        "help_faq_tesseract_windows_answer",
        "help_faq_tesseract_macos_question",
        "help_faq_tesseract_macos_answer",
        "help_faq_tesseract_linux_question",
        "help_faq_tesseract_linux_answer",
        "help_faq_azure_question",
        "help_faq_azure_answer",
        "help_faq_local_fallback_question",
        "help_faq_local_fallback_answer",
    ]

    for lang in ["en", "zh_CN"]:
        for key in required_keys:
            assert key in TRANSLATIONS[lang]
