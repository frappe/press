# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from cdktf import Fn
from cdktf_cdktf_provider_digitalocean.droplet import Droplet
from cdktf_cdktf_provider_digitalocean.project import Project
from cdktf_cdktf_provider_digitalocean.provider import DigitaloceanProvider
from cdktf_cdktf_provider_digitalocean.volume import Volume
from cdktf_cdktf_provider_digitalocean.volume_attachment import VolumeAttachment
from constructs import Construct

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from press.press.doctype.cloud_region.cloud_region import CloudRegion
	from press.provision.doctype.provider.provider import Provider
	from press.press.opentofu import PilotStack


class DigitalOcean:
	def provision(self, stack: "PilotStack", scope: Construct, name: str, region: "CloudRegion", provider: "Provider") -> None:
		DigitaloceanProvider(stack, "digitalocean", token=provider.get_password("secret"))
		droplet = Droplet(
			stack,
			f"{name}_droplet",
			image="ubuntu-20-04-x64",
			name=f"{name}-droplet-1",
			region=region.region_name,
			size="s-1`vcpu-1gb",
			ssh_keys=["39020628"],
		)

		volume = Volume(
			stack,
			f"{name}_volume",
			region=region.region_name,
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
