import pandas as pd
from backend.utils.schema import (
    normalize_country,
    get_country_iso3,
    detect_and_normalize_columns,
)


class TestNormalizeCountry:
    def test_exact_match(self):
        assert normalize_country("germany") == "GERMANY"

    def test_strips_quotes_and_whitespace(self):
        assert normalize_country("  'Germany' ") == "GERMANY"

    def test_exact_match_including_multiword_key(self):
        # "BANGLADESH PR" is itself a literal key in COUNTRY_MAP_ISO, so
        # this resolves via the exact-match branch, not fuzzy matching.
        assert normalize_country("Bangladesh Pr") == "BANGLADESH PR"

    def test_fuzzy_substring_match(self):
        # "Republic of Korea" isn't a key itself, but contains "KOREA" as
        # a substring - the fuzzy fallback loop should catch this and
        # return the matching key ("KOREA"), not the raw cleaned input.
        assert normalize_country("Republic of Korea") == "KOREA"

    def test_non_string_input_returns_unknown(self):
        assert normalize_country(None) == "UNKNOWN"
        assert normalize_country(12345) == "UNKNOWN"

    def test_unrecognized_country_passes_through_cleaned(self):
        # Not in COUNTRY_MAP_ISO - should return the cleaned string as-is,
        # not crash or silently drop it.
        assert normalize_country("atlantis") == "ATLANTIS"


class TestGetCountryIso3:
    def test_known_country(self):
        assert get_country_iso3("Germany") == "DEU"
        assert get_country_iso3("USA") == "USA"
        assert get_country_iso3("Vietnam Soc Rep") == "VNM"

    def test_unknown_country_defaults_to_world_code(self):
        assert get_country_iso3("Nonexistent Country XYZ") == "W00"


class TestDetectAndNormalizeColumns:
    def test_standard_messy_headers_get_mapped(self):
        # Realistic messy real-world column names, not the clean ones
        df = pd.DataFrame({
            "Cmd Code": ["520100"],
            "PartnerDesc": ["Germany"],
            "FOBValue": [1000.0],
            "Qty_Tons": [5.0],
            "RefYear": [2024],
        })
        result = detect_and_normalize_columns(df)

        assert "hs_code" in result.columns
        assert "country" in result.columns
        assert "value" in result.columns
        assert "quantity" in result.columns
        assert "year" in result.columns
        assert result["country"].iloc[0] == "Germany"
        assert result["value"].iloc[0] == 1000.0

    def test_unrecognized_columns_returned_unchanged(self):
        df = pd.DataFrame({"totally_unrelated_column": [1, 2, 3]})
        result = detect_and_normalize_columns(df)
        # No column matched any known pattern - original df passed through
        assert list(result.columns) == ["totally_unrelated_column"]

    def test_tradestat_eidb_format_detected_and_parsed(self):
        # Mimics the double-header TradeStat->Eidb Excel export: one
        # actual column name contains the marker text, row 0 is a
        # secondary junk header row (skipped), real data starts at row 1.
        raw = pd.DataFrame(
            data=[
                ["S.No.", "Country / Region", "2023-2024", "2024-2025", "%Growth", "2023-2024", "2024-2025", "%Growth"],
                [1, "Germany", "1.5", "2.0", "33", "500", "600", "20"],
                [2, "Total", "10", "12", "20", "3000", "3200", "6"],  # should be skipped
            ],
            columns=["TradeStat->Eidb", "c1", "c2", "c3", "c4", "c5", "c6", "c7"],
        )
        result = detect_and_normalize_columns(raw)

        assert not result.empty
        countries = result["country"].tolist()
        assert "Germany" in countries
        assert "Total" not in countries
        # Value column should be in USD (millions -> raw), not left in millions
        germany_row = result[(result["country"] == "Germany") & (result["year"] == 2023)]
        assert germany_row["value"].iloc[0] == 1.5 * 1_000_000
