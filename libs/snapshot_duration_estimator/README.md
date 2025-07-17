Snapshot Time Estimator

## Overview

Based on past 6 months of data, train a small ML model based on Random Forest Regressor.

This can help to predict amount of time AWS/OCI can take to make the snapshot available to user.

### Features

Based on the past data and correlation matrix, two features correlates with duration

- Total amount of writes from last successful snapshot till now
- max_p99_iops between current time and the last successful snapshot

### Training Guide

1. For disk stats, we will fetch the data from prometheus. So set this environment variables locally - `MONITORING_SERVER_BASE_URL`, `MONITORING_SERVER_USER`, `MONITORING_SERVER_PASSWORD`
2. For snapshot details, go to `Virtual Disk Snapshot` doctype. Pick these columns - `Virtual Machine`,`Size`, `Start Time`,`Duration` and download a report in csv format with name `snapshot.csv`
3. You can run the main.py directly to parse all data and then train the model. Check the `main.py` for the steps.

### Sample Code For Prediction

```python
from functools import lru_cache
import joblib


class SnapshotTimeEstimator:
    _model = None
    _model_path = "snapshot_time_estimator.pkl"

    @staticmethod
    def get_model():
        if not SnapshotTimeEstimator._model:
            SnapshotTimeEstimator._model = joblib.load(
                SnapshotTimeEstimator._model_path
            )
        return SnapshotTimeEstimator._model

    @staticmethod
    @lru_cache
    def predict(total_writes_gb: int, max_p99_iops_usage: int) -> float:
        """
        Predict the snapshot time based on the provided features.

        :param total_writes_gb: Total writes in GB between current and last successful snapshot
        :param max_p99_iops_usage: Maximum P99 IOPS usage between current and last successful snapshot
        :return: Predicted snapshot time in seconds
        """
        return SnapshotTimeEstimator.get_model().predict(
            [[total_writes_gb, max_p99_iops_usage]]
        )[0]

```
