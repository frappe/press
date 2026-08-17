# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json
from datetime import datetime, timedelta

import boto3
import frappe
from frappe.utils import flt

from press.utils.aws import EXCLUDED_REGIONS, get_press_aws_credentials

BYTES_PER_GB = 1024**3
TRAILING_DAYS = 14

# CloudWatch publishes BucketSizeBytes separately per storage class — there is no
# combined "all classes" size metric — mapped to the AWS Pricing API's volumeType
# for that class. Rarely-used overhead/staging sub-metrics are not covered.
STORAGE_TYPES = {
	"StandardStorage": "Standard",
	"StandardIAStorage": "Standard - Infrequent Access",
	"OneZoneIAStorage": "One Zone - Infrequent Access",
	"IntelligentTieringFAStorage": "Intelligent-Tiering",
	"GlacierStorage": "Glacier",
	"DeepArchiveStorage": "Glacier Deep Archive",
	"ReducedRedundancyStorage": "Reduced Redundancy",
}


def execute(filters=None):
	frappe.only_for("System Manager")
	filters = filters or {}

	buckets = get_buckets(filters)
	pricing_client = get_pricing_client()

	rows = [build_row(bucket, pricing_client) for bucket in buckets]
	rows.sort(key=lambda row: row["current_size_gb"], reverse=True)

	columns = get_columns()
	report_summary = get_report_summary(rows)
	return columns, rows, None, None, report_summary


def get_buckets(filters):
	credentials = get_press_aws_credentials()
	client = boto3.client("s3", region_name="us-east-1", **credentials)

	buckets = []
	for bucket in client.list_buckets()["Buckets"]:
		name = bucket["Name"]
		if filters.get("bucket") and filters["bucket"].lower() not in name.lower():
			continue

		region = get_bucket_region(client, name)
		if region in EXCLUDED_REGIONS:
			continue
		buckets.append({"name": name, "region": region, "credentials": credentials})
	return buckets


def get_bucket_region(client, bucket_name):
	location = client.get_bucket_location(Bucket=bucket_name)["LocationConstraint"]
	return location or "us-east-1"


def build_row(bucket, pricing_client):
	series_by_type = get_bucket_storage_series(bucket)
	breakdown = {storage_type: series[-1]["size"] for storage_type, series in series_by_type.items()}
	current_size = sum(breakdown.values())
	monthly_cost, unpriced_size = get_monthly_storage_cost(pricing_client, bucket["region"], breakdown)

	size_history = get_combined_daily_history(series_by_type)
	weekly_growth, prior_weekly_growth = get_weekly_growth(size_history)
	growth_change_percent = (
		((weekly_growth - prior_weekly_growth) / prior_weekly_growth * 100) if prior_weekly_growth else 0
	)

	return {
		"bucket": bucket["name"],
		"region": bucket["region"],
		"current_size_gb": flt(current_size / BYTES_PER_GB, 2),
		"object_count": get_latest_object_count(bucket),
		"monthly_cost": monthly_cost,
		"unpriced_size_gb": unpriced_size,
		"daily_growth_gb": flt(weekly_growth / BYTES_PER_GB / 7, 3),
		"weekly_growth_gb": flt(weekly_growth / BYTES_PER_GB, 2),
		"growth_change_percent": flt(growth_change_percent, 1),
	}


def get_cloudwatch_client(bucket):
	return boto3.client("cloudwatch", region_name=bucket["region"], **bucket["credentials"])


def get_bucket_storage_series(bucket):
	"""Daily size series per storage class, for whichever classes this bucket
	actually has data for (a class with no objects returns no datapoints)."""
	series_by_type = {}
	for storage_type in STORAGE_TYPES:
		series = get_storage_type_series(bucket, storage_type)
		if series:
			series_by_type[storage_type] = series
	return series_by_type


def get_storage_type_series(bucket, storage_type):
	client = get_cloudwatch_client(bucket)
	end = datetime.utcnow()
	start = end - timedelta(days=TRAILING_DAYS + 1)

	response = client.get_metric_statistics(
		Namespace="AWS/S3",
		MetricName="BucketSizeBytes",
		Dimensions=[
			{"Name": "BucketName", "Value": bucket["name"]},
			{"Name": "StorageType", "Value": storage_type},
		],
		StartTime=start,
		EndTime=end,
		Period=86400,
		Statistics=["Average"],
	)

	datapoints = sorted(response["Datapoints"], key=lambda point: point["Timestamp"])
	return [{"timestamp": point["Timestamp"], "size": point["Average"]} for point in datapoints]


def get_combined_daily_history(series_by_type):
	"""Sum per-class series into one total-size-per-day history.
	Reflects net size change, not gross bytes uploaded — S3 request-level upload
	metrics require per-bucket CloudWatch request metrics, which aren't assumed enabled."""
	size_by_date = {}
	for series in series_by_type.values():
		for point in series:
			date = point["timestamp"].date()
			size_by_date[date] = size_by_date.get(date, 0) + point["size"]
	return [{"size": size} for _, size in sorted(size_by_date.items())]


def get_latest_object_count(bucket):
	client = get_cloudwatch_client(bucket)
	end = datetime.utcnow()
	start = end - timedelta(days=3)

	response = client.get_metric_statistics(
		Namespace="AWS/S3",
		MetricName="NumberOfObjects",
		Dimensions=[
			{"Name": "BucketName", "Value": bucket["name"]},
			{"Name": "StorageType", "Value": "AllStorageTypes"},
		],
		StartTime=start,
		EndTime=end,
		Period=86400,
		Statistics=["Average"],
	)

	datapoints = sorted(response["Datapoints"], key=lambda point: point["Timestamp"])
	return int(datapoints[-1]["Average"]) if datapoints else 0


def get_weekly_growth(size_history):
	"""Net size change over the trailing week, and the week before that."""
	sizes = [point["size"] for point in size_history]
	this_week = sizes[-7:]
	prior_week = sizes[-14:-7]

	this_week_growth = this_week[-1] - this_week[0] if len(this_week) >= 2 else 0
	prior_week_growth = prior_week[-1] - prior_week[0] if len(prior_week) >= 2 else 0
	return this_week_growth, prior_week_growth


def get_pricing_client():
	return boto3.client("pricing", region_name="ap-south-1", **get_press_aws_credentials())


def get_monthly_storage_cost(client, region, breakdown):
	"""Price each storage class at its own rate — first pricing tier only, a
	reasonable approximation for buckets under ~50TB. Bytes in a class this
	can't find a price for are counted as size but reported as unpriced,
	rather than silently priced at $0 or folded into the Standard rate."""
	total_cost = 0
	unpriced_bytes = 0
	for storage_type, size_bytes in breakdown.items():
		price_per_gb = get_s3_price_per_gb(client, region, STORAGE_TYPES[storage_type])
		if price_per_gb is None:
			unpriced_bytes += size_bytes
			continue
		total_cost += price_per_gb * (size_bytes / BYTES_PER_GB)
	return flt(total_cost, 2), flt(unpriced_bytes / BYTES_PER_GB, 2)


def get_s3_price_per_gb(client, region, volume_type):
	product_filters = [
		{"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
		{"Type": "TERM_MATCH", "Field": "volumeType", "Value": volume_type},
	]

	response = client.get_products(ServiceCode="AmazonS3", Filters=product_filters, MaxResults=1)
	for item in response["PriceList"]:
		product = json.loads(item)
		for term in product["terms"].get("OnDemand", {}).values():
			dimension = next(iter(term["priceDimensions"].values()))
			usd_price = dimension["pricePerUnit"].get("USD")
			if usd_price is not None:
				return flt(usd_price)
	return None


def get_columns():
	return [
		{"fieldname": "bucket", "label": "Bucket", "fieldtype": "Data", "width": 220},
		{"fieldname": "region", "label": "Region", "fieldtype": "Data", "width": 110},
		{"fieldname": "current_size_gb", "label": "Current Size (GB)", "fieldtype": "Float", "width": 130},
		{"fieldname": "object_count", "label": "Object Count", "fieldtype": "Int", "width": 110},
		{
			"fieldname": "monthly_cost",
			"label": "Est. Monthly Storage Cost (USD)",
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"fieldname": "unpriced_size_gb",
			"label": "Unpriced Size (GB)",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"fieldname": "daily_growth_gb",
			"label": "Daily Avg Growth (GB/day)",
			"fieldtype": "Float",
			"width": 150,
		},
		{"fieldname": "weekly_growth_gb", "label": "Weekly Growth (GB)", "fieldtype": "Float", "width": 130},
		{
			"fieldname": "growth_change_percent",
			"label": "Growth Change vs Prior Week (%)",
			"fieldtype": "Percent",
			"width": 180,
		},
	]


def get_report_summary(rows):
	total_size = sum(row["current_size_gb"] for row in rows)
	total_cost = sum(row["monthly_cost"] for row in rows)
	total_unpriced = sum(row["unpriced_size_gb"] for row in rows)
	total_weekly_growth = sum(row["weekly_growth_gb"] for row in rows)

	return [
		{"value": len(rows), "label": "Buckets", "datatype": "Int", "indicator": "blue"},
		{
			"value": flt(total_size, 2),
			"label": "Total Storage (GB)",
			"datatype": "Float",
			"indicator": "blue",
		},
		{
			"value": flt(total_cost, 2),
			"label": "Total Estimated Monthly Cost (USD)",
			"datatype": "Currency",
			"indicator": "blue",
		},
		{
			"value": flt(total_unpriced, 2),
			"label": "Unpriced Storage (GB)",
			"datatype": "Float",
			"indicator": "red",
		},
		{
			"value": flt(total_weekly_growth, 2),
			"label": "Total Weekly Growth (GB)",
			"datatype": "Float",
			"indicator": "orange",
		},
	]
