# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CloudRegion(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		provider: DF.Literal["AWS EC2", "OCI", "Hetzner", "DigitalOcean", "Frappe Compute"]
		region_name: DF.Data
	# end: auto-generated types

	pass


# The city and the ISO country code of each region code that Press can meet:
# the S3 regions of the backup buckets and the regions of the clusters. The
# dashboard shows the city and the flag of the country for a region that has
# no cluster with a flag.
REGION_LOCATIONS: dict[str, tuple[str, str]] = {
	# AWS
	"us-east-1": ("N. Virginia", "us"),
	"us-east-2": ("Ohio", "us"),
	"us-west-1": ("N. California", "us"),
	"us-west-2": ("Oregon", "us"),
	"af-south-1": ("Cape Town", "za"),
	"ap-east-1": ("Hong Kong", "hk"),
	"ap-south-1": ("Mumbai", "in"),
	"ap-south-2": ("Hyderabad", "in"),
	"ap-southeast-1": ("Singapore", "sg"),
	"ap-southeast-2": ("Sydney", "au"),
	"ap-southeast-3": ("Jakarta", "id"),
	"ap-southeast-4": ("Melbourne", "au"),
	"ap-southeast-5": ("Kuala Lumpur", "my"),
	"ap-southeast-7": ("Bangkok", "th"),
	"ap-northeast-1": ("Tokyo", "jp"),
	"ap-northeast-2": ("Seoul", "kr"),
	"ap-northeast-3": ("Osaka", "jp"),
	"ca-central-1": ("Montreal", "ca"),
	"ca-west-1": ("Calgary", "ca"),
	"eu-central-1": ("Frankfurt", "de"),
	"eu-central-2": ("Zurich", "ch"),
	"eu-west-1": ("Ireland", "ie"),
	"eu-west-2": ("London", "gb"),
	"eu-west-3": ("Paris", "fr"),
	"eu-north-1": ("Stockholm", "se"),
	"eu-south-1": ("Milan", "it"),
	"eu-south-2": ("Spain", "es"),
	"il-central-1": ("Tel Aviv", "il"),
	"me-south-1": ("Bahrain", "bh"),
	"me-central-1": ("UAE", "ae"),
	"mx-central-1": ("Mexico", "mx"),
	"sa-east-1": ("São Paulo", "br"),
	# Hetzner
	"nbg1": ("Nuremberg", "de"),
	"fsn1": ("Falkenstein", "de"),
	"hel1": ("Helsinki", "fi"),
	"ash": ("Ashburn", "us"),
	"hil": ("Hillsboro", "us"),
	"sin": ("Singapore", "sg"),
	# DigitalOcean
	"nyc1": ("New York", "us"),
	"nyc3": ("New York", "us"),
	"sfo2": ("San Francisco", "us"),
	"sfo3": ("San Francisco", "us"),
	"tor1": ("Toronto", "ca"),
	"ams3": ("Amsterdam", "nl"),
	"lon1": ("London", "gb"),
	"fra1": ("Frankfurt", "de"),
	"sgp1": ("Singapore", "sg"),
	"blr1": ("Bangalore", "in"),
	"syd1": ("Sydney", "au"),
}


def get_flag_url(country_code: str) -> str:
	"""The flag of a country, from the same source as the phone input of the dashboard."""
	return f"https://flagcdn.com/w40/{country_code}.png"
