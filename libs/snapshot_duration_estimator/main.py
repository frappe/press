from model import (
	build_dataset,
	build_model,
	feed_snapshot_details,
	fetch_all_disk_stats,
)

"""
Steps to generate the dataset:
1. First run `fetch_all_disk_stats()` to collect disk stats.
2. Then run `feed_snapshot_details()` to process stored snapshot.csv
3. Finally, run `build_dataset()` to create the dataset.
4. Run `build_model()` to train the model.

Check the function signatures in `data_scrapper.py` for more details.
"""


if __name__ == "__main__":
	fetch_all_disk_stats()
	feed_snapshot_details()
	build_dataset()
	build_model()
