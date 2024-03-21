<template>
	<div v-if="clusterDoc?.doc" class="grid grid-cols-1 items-start gap-5 mt-5">
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">
					Security Group Information
				</h2>
			</div>
			<div>
				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base text-gray-700">Security Group Id</div>
					<div class="w-2/3 text-base font-medium">
						{{ securityGroupInformation.security_group_id }}
					</div>
				</div>
				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base text-gray-700">Security Group Name</div>
					<div class="w-2/3 text-base font-medium">
						{{ securityGroupInformation.security_group_name }}
					</div>
				</div>

				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base font-medium">Protocol</div>
					<div class="w-1/3 text-base font-medium">From Port</div>
					<div class="w-1/3 text-base font-medium">To Port</div>
					<div class="w-2/3 text-base font-medium">CidrIp</div>
					<div class="w-2/3 text-base font-medium">Description</div>
				</div>
				<div
					v-for="d in securityGroupInformation.security_group_rules"
					:key="d.FromPort"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base font-medium">{{ d.IpProtocol }}</div>
					<div class="w-1/3 text-base font-medium">{{ d.FromPort }}</div>
					<div class="w-1/3 text-base font-medium">{{ d.ToPort }}</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.IpRanges[0].CidrIp }}
					</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.IpRanges[0].Description }}
					</div>
				</div>
			</div>
		</div>
	</div>
	<div v-if="clusterDoc?.doc" class="grid grid-cols-1 items-start gap-5 mt-5">
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">
					Proxy Security Group Information
				</h2>
			</div>
			<div>
				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base text-gray-700">Security Group Id</div>
					<div class="w-2/3 text-base font-medium">
						{{ securityGroupInformation.proxy_security_group_id }}
					</div>
				</div>
				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base text-gray-700">Security Group Name</div>
					<div class="w-2/3 text-base font-medium">
						{{ securityGroupInformation.proxy_security_group_name }}
					</div>
				</div>

				<div class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70">
					<div class="w-1/3 text-base font-medium">Protocol</div>
					<div class="w-1/3 text-base font-medium">From Port</div>
					<div class="w-1/3 text-base font-medium">To Port</div>
					<div class="w-2/3 text-base font-medium">CidrIp</div>
					<div class="w-2/3 text-base font-medium">Description</div>
				</div>
				<div
					v-for="d in securityGroupInformation.proxy_security_group_rules"
					:key="d.FromPort"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base font-medium">{{ d.IpProtocol }}</div>
					<div class="w-1/3 text-base font-medium">{{ d.FromPort }}</div>
					<div class="w-1/3 text-base font-medium">{{ d.ToPort }}</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.IpRanges[0].CidrIp }}
					</div>
					<div class="w-2/3 text-base font-medium">
						{{ d.IpRanges[0].Description }}
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'AWSClusterNetworkOverview',
	props: ['cluster', 'clusterDoc', 'securityGroupInformation']
};
</script>
