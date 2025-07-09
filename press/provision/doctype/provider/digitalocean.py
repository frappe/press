# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from typing import TYPE_CHECKING

from cdktf import Fn
from cdktf_cdktf_provider_digitalocean.droplet import Droplet
from cdktf_cdktf_provider_digitalocean.project import Project
from cdktf_cdktf_provider_digitalocean.provider import DigitaloceanProvider
from cdktf_cdktf_provider_digitalocean.volume import Volume
from cdktf_cdktf_provider_digitalocean.volume_attachment import VolumeAttachment
from cdktf_cdktf_provider_digitalocean.vpc import Vpc
from constructs import Construct

if TYPE_CHECKING:
	from press.press.doctype.region.region import Region

class DigitalOcean:
	def provision(self, stack: "PilotStack", scope: Construct, name: str, region: "Region") -> None:
		DigitaloceanProvider(stack, "digitalocean", token=region.get_password("access_token"))
		vpc = Vpc(
			stack,
			f"{name}_vpc",
			name=f"{name}-vpc-1",
			region=region.region_slug,
			ip_range=region.vpc_cidr_block,
		)

		droplet = Droplet(
			stack,
			f"{name}_droplet",
			image="ubuntu-24-04-x64",
			name=f"{name}-droplet-1",
			region=region.region_slug,
			size="s-1vcpu-1gb",
			vpc_uuid=vpc.id,
			ssh_keys=["39020628"],
		)

		volume = Volume(
			stack,
			f"{name}_volume",
			region=region.region_slug,
			name=f"{name}-volume-1",
			size=10,
			initial_filesystem_type="ext4",
			description="an example volume",
		)

		VolumeAttachment(
			stack,
			f"{name}_volume_attachment",
			droplet_id=Fn.tonumber(droplet.id),
			volume_id=volume.id,
		)

		Project(
			stack,
			f"{name}_project",
			name="Pilot Tofu Playground",
			description="Project for playing around with Tofu",
			purpose="Web Application",
			environment="Development",
			resources=[droplet.urn],
		)
