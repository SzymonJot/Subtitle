request = {
    "analyzed_hash": "c0ffee12-3456-789a-bcde-0123456789ab",
    "target_coverage": None,
    "max_cards": 100,
    # "max_share_per_pos": {"NOUN": 0.6, "VERB": 0.2, 'ADJ':0.1},
    "target_share_per_pos": {"NOUN": 0.5, "VERB": 0.5},
    "exclude_known_lemmas": ["vara", "ha", "och", "att"],
    "dedupe_sentences": True,
    "difficulty_scoring": "FREQ",
    "output_format": "ANKI",
    "example_settings": {
        "example_len": {"min_example_word_count": 2, "max_example_word_count": 15}
    },
    "lang_opts": {"sv": {}},
    "build_version": "2025-10-09.b3",
    "params_schema_version": "v1",
    "requested_by": "szymon@example.com",
    "requested_at_iso": "2025-10-09T21:12:00+02:00",
    "target_lang_tag": "en",
}
