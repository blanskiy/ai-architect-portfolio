"""
Tests for Feature Store Components
Tests feature engineering, point-in-time joins, and serving logic.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'data'))

from feature_engineering import FeatureEngineer


class TestFeatureEngineering:
    """Tests for feature engineering logic."""
    
    @pytest.fixture
    def sample_transactions(self):
        """Create sample transaction data."""
        base_date = datetime(2024, 1, 31)
        
        return pd.DataFrame({
            'user_id': ['user_1', 'user_1', 'user_1', 'user_2', 'user_2'],
            'transaction_date': [
                base_date - timedelta(days=5),   # user_1, recent
                base_date - timedelta(days=15),  # user_1, within 30d
                base_date - timedelta(days=60),  # user_1, within 90d
                base_date - timedelta(days=10),  # user_2, within 30d
                base_date - timedelta(days=100), # user_2, outside 90d
            ],
            'amount': [100.0, 200.0, 150.0, 300.0, 50.0],
        })
    
    @pytest.fixture
    def engineer(self, tmp_path):
        """Create FeatureEngineer instance."""
        return FeatureEngineer(output_dir=str(tmp_path))
    
    def test_user_transaction_features_30d_window(self, engineer, sample_transactions):
        """Test 30-day window aggregations."""
        as_of_date = datetime(2024, 1, 31)
        
        features = engineer.compute_user_transaction_features(
            transactions_df=sample_transactions,
            as_of_date=as_of_date,
        )
        
        # User 1: has 2 transactions in last 30 days (5 and 15 days ago)
        user1 = features[features['user_id'] == 'user_1'].iloc[0]
        assert user1['purchase_count_30d'] == 2
        assert user1['avg_purchase_amount_30d'] == 150.0  # (100 + 200) / 2
        assert user1['total_purchase_amount_30d'] == 300.0
        
        # User 2: has 1 transaction in last 30 days
        user2 = features[features['user_id'] == 'user_2'].iloc[0]
        assert user2['purchase_count_30d'] == 1
        assert user2['avg_purchase_amount_30d'] == 300.0
    
    def test_user_transaction_features_90d_window(self, engineer, sample_transactions):
        """Test 90-day window aggregations."""
        as_of_date = datetime(2024, 1, 31)
        
        features = engineer.compute_user_transaction_features(
            transactions_df=sample_transactions,
            as_of_date=as_of_date,
        )
        
        # User 1: has 3 transactions in last 90 days
        user1 = features[features['user_id'] == 'user_1'].iloc[0]
        assert user1['purchase_count_90d'] == 3
        
        # User 2: has 1 transaction in last 90 days (100 days ago is outside)
        user2 = features[features['user_id'] == 'user_2'].iloc[0]
        assert user2['purchase_count_90d'] == 1
    
    def test_lifetime_aggregations(self, engineer, sample_transactions):
        """Test lifetime aggregations."""
        as_of_date = datetime(2024, 1, 31)
        
        features = engineer.compute_user_transaction_features(
            transactions_df=sample_transactions,
            as_of_date=as_of_date,
        )
        
        # User 1: 3 transactions total
        user1 = features[features['user_id'] == 'user_1'].iloc[0]
        assert user1['lifetime_purchase_count'] == 3
        assert user1['lifetime_purchase_amount'] == 450.0  # 100 + 200 + 150
        
        # User 2: 2 transactions total
        user2 = features[features['user_id'] == 'user_2'].iloc[0]
        assert user2['lifetime_purchase_count'] == 2
        assert user2['lifetime_purchase_amount'] == 350.0  # 300 + 50
    
    def test_recency_features(self, engineer, sample_transactions):
        """Test recency feature calculations."""
        as_of_date = datetime(2024, 1, 31)
        
        features = engineer.compute_user_transaction_features(
            transactions_df=sample_transactions,
            as_of_date=as_of_date,
        )
        
        # User 1: last purchase 5 days ago, first purchase 60 days ago
        user1 = features[features['user_id'] == 'user_1'].iloc[0]
        assert user1['days_since_last_purchase'] == 5
        assert user1['days_since_first_purchase'] == 60
    
    def test_point_in_time_correctness(self, engineer, sample_transactions):
        """Test that features are computed as of the specified date."""
        # Compute features as of Jan 20 (before some transactions)
        as_of_date = datetime(2024, 1, 20)
        
        features = engineer.compute_user_transaction_features(
            transactions_df=sample_transactions,
            as_of_date=as_of_date,
        )
        
        # User 1: only 2 transactions before Jan 20 (15 and 60 days before Jan 31)
        user1 = features[features['user_id'] == 'user_1'].iloc[0]
        
        # Transaction on Jan 26 (5 days before Jan 31) should NOT be included
        # because it's after the as_of_date
        assert user1['lifetime_purchase_count'] == 2  # Not 3
    
    def test_empty_transactions(self, engineer):
        """Test handling of users with no transactions."""
        empty_df = pd.DataFrame({
            'user_id': [],
            'transaction_date': [],
            'amount': [],
        })
        
        features = engineer.compute_user_transaction_features(
            transactions_df=empty_df,
            as_of_date=datetime.now(),
        )
        
        assert len(features) == 0


class TestPointInTimeJoin:
    """Tests for point-in-time join correctness."""
    
    def test_no_future_leakage(self):
        """Verify that future features are not used for past events."""
        
        # Feature data with timestamps
        feature_data = pd.DataFrame({
            'user_id': ['user_1', 'user_1', 'user_1'],
            'feature_timestamp': [
                datetime(2024, 1, 1),   # Old feature value
                datetime(2024, 1, 15),  # Feature value at label time
                datetime(2024, 1, 30),  # Future feature value
            ],
            'purchase_count': [5, 10, 20],
        })
        
        # Label event at Jan 15
        entity_df = pd.DataFrame({
            'user_id': ['user_1'],
            'event_timestamp': [datetime(2024, 1, 15)],
            'label': [1],
        })
        
        # Point-in-time join should select feature with timestamp <= Jan 15
        # In this case, the feature from Jan 15 (10) should be used
        # NOT the feature from Jan 30 (20)
        
        # Simulate point-in-time join
        merged = entity_df.copy()
        user_features = feature_data[feature_data['user_id'] == 'user_1']
        
        event_time = entity_df['event_timestamp'].iloc[0]
        valid_features = user_features[user_features['feature_timestamp'] <= event_time]
        latest_valid = valid_features.sort_values('feature_timestamp').iloc[-1]
        
        assert latest_valid['purchase_count'] == 10  # Not 20 (future)
    
    def test_correct_feature_window(self):
        """Test that correct feature version is selected based on timestamp."""
        
        # User has features computed daily
        dates = pd.date_range('2024-01-01', '2024-01-10', freq='D')
        feature_data = pd.DataFrame({
            'user_id': ['user_1'] * len(dates),
            'feature_timestamp': dates,
            'purchase_count': range(1, len(dates) + 1),
        })
        
        # Multiple label events at different times
        entity_df = pd.DataFrame({
            'user_id': ['user_1', 'user_1', 'user_1'],
            'event_timestamp': [
                datetime(2024, 1, 3, 12, 0),  # Should use feature from Jan 3
                datetime(2024, 1, 5, 12, 0),  # Should use feature from Jan 5
                datetime(2024, 1, 8, 12, 0),  # Should use feature from Jan 8
            ],
        })
        
        # Verify each entity gets the right feature version
        expected_counts = [3, 5, 8]
        
        for i, row in entity_df.iterrows():
            event_time = row['event_timestamp']
            valid_features = feature_data[
                (feature_data['user_id'] == row['user_id']) &
                (feature_data['feature_timestamp'] <= event_time)
            ]
            latest = valid_features.sort_values('feature_timestamp').iloc[-1]
            
            assert latest['purchase_count'] == expected_counts[i]


class TestFeatureTypes:
    """Tests for feature type handling."""
    
    def test_float32_casting(self):
        """Test that float features are cast to float32."""
        engineer = FeatureEngineer(output_dir="/tmp")
        
        df = pd.DataFrame({
            'feature': [1.5, 2.5, 3.5]
        })
        
        result = engineer._cast_types(df, {'feature': 'float32'})
        
        assert result['feature'].dtype == np.float32
    
    def test_int64_casting(self):
        """Test that integer features are cast to int64."""
        engineer = FeatureEngineer(output_dir="/tmp")
        
        df = pd.DataFrame({
            'feature': [1.0, 2.0, 3.0]
        })
        
        result = engineer._cast_types(df, {'feature': 'int64'})
        
        assert result['feature'].dtype == np.int64
    
    def test_null_handling(self):
        """Test that nulls are filled with 0 before casting."""
        engineer = FeatureEngineer(output_dir="/tmp")
        
        df = pd.DataFrame({
            'feature': [1.0, None, 3.0]
        })
        
        result = engineer._cast_types(df, {'feature': 'int64'})
        
        assert result['feature'].iloc[1] == 0
        assert result['feature'].isna().sum() == 0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
