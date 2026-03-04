import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from raw_ingest.ingest_swapi_characters import ingest_swapi_characters

def test_ingest_swapi_characters_first_run(mock_logger):
    # Setup mocks
    with patch("raw_ingest.ingest_swapi_characters.SwapiFetcher") as MockFetcher, \
         patch("raw_ingest.ingest_swapi_characters.DbWriter") as MockWriter, \
         patch("raw_ingest.ingest_swapi_characters.SparkSession") as MockSpark:
        
        mock_spark = MagicMock()
        MockSpark.builder.getOrCreate.return_value = mock_spark
        
        fetcher_inst = MockFetcher.return_value
        fetcher_inst.full_path_table_name = "agent.bronze__raw_api.characters"
        fetcher_inst.fetch_historical_data.return_value = pd.DataFrame([{"name": "Luke", "created": "2024-01-01"}])
        
        # Simulate table not found
        mock_spark.read.table.side_effect = Exception("Table not found")
        
        success = ingest_swapi_characters("agent", "bronze__raw_api")
        
        assert success is True
        fetcher_inst.fetch_historical_data.assert_called_once_with()
        MockWriter.assert_called_once()
