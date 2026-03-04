import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from raw_ingest.SwapiFetcher import SwapiFetcher

def test_swapi_fetcher_init(mock_logger):
    fetcher = SwapiFetcher(logger=mock_logger, catalog="agent", schema="bronze__raw_api")
    assert fetcher.catalog == "agent"
    assert fetcher.schema == "bronze__raw_api"
    assert fetcher.table_name == "characters"

@patch("raw_ingest.SwapiFetcher.requests.get")
def test_fetch_swapi_characters(mock_get, mock_swapi_api_response, mock_logger):
    # Mock API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = [mock_swapi_api_response]
    mock_get.return_value = mock_response

    fetcher = SwapiFetcher(logger=mock_logger, catalog="agent", schema="bronze__raw_api")
    df = fetcher.fetch_characters()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Luke Skywalker"
    assert "films" in df.columns
    # Verify exact raw columns (no renaming)
    assert "birth_year" in df.columns
