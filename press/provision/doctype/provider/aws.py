from cdktf import App, TerraformStack
from cdktf_cdktf_provider_aws.ebs_volume import EbsVolume
from cdktf_cdktf_provider_aws.instance import Instance
from cdktf_cdktf_provider_aws.provider import AwsProvider
from cdktf_cdktf_provider_aws.volume_attachment import VolumeAttachment
from constructs import Construct


class SimpleProviderStack(TerraformStack):
	def __init__(self, scope: Construct, id: str, region: str):
		super().__init__(scope, id)

		AwsProvider(
			self,
			"aws",
			region="f{region}",
		)

		Instance(
			self,
			"hello",
			ami="ami-2757f631",
			instance_type="t2.micro",
		)

		# Create EBS Volume
		volume = EbsVolume(self, "storage", availability_zone="us-west-2a", size=20, type="gp3")

		# Attach volume to instance
		VolumeAttachment(
			self,
			"volume_attachment",
			device_name="/dev/sdf",
			volume_id=volume.id,
			instance_id=Instance(self, "hello").id,
		)


app = App()
SimpleProviderStack(app, "provider-stack")
app.synth()
