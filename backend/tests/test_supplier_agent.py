from backend.agents.supplier_agent import _extract_state


class TestExtractState:
    def test_recognizes_standard_state_name(self):
        assert _extract_state("VARANASI-221001 UTTAR PRADESH") == "Uttar Pradesh"

    def test_handles_known_typo_in_source_data(self):
        # "MAHARASHT RA" (split with a stray space) is a real typo present
        # in the source dataset - must still resolve correctly.
        assert _extract_state("KOLHAPUR-416115 MAHARASHT RA") == "Maharashtra"

    def test_handles_known_misspelling(self):
        assert _extract_state("SOME CITY-000000 GUJRAT") == "Gujarat"

    def test_non_string_input_returns_unknown(self):
        assert _extract_state(None) == "Unknown"
        assert _extract_state(12345) == "Unknown"

    def test_fallback_hyphen_parsing_for_unmapped_state(self):
        # No known state name present - falls back to text after the last
        # hyphen, with digits stripped
        result = _extract_state("SOME CITY-000000ZANYSTATE")
        assert result == "Zanystate"

    def test_no_hyphen_and_no_match_returns_other(self):
        assert _extract_state("COMPLETELY UNSTRUCTURED TEXT") == "Other"
