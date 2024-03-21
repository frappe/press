<template>
	<div
		v-if="clusterDoc?.doc"
		class="grid grid-cols-1 items-start gap-5 sm:grid-cols-2"
	>
		<div class="rounded-md border">
			<div class="h-12 border-b px-5 py-4">
				<h2 class="text-lg font-medium text-gray-900">Cluster Information</h2>
			</div>
			<div>
				<div
					v-for="d in clusterInformation"
					:key="d.label"
					class="flex items-center px-5 py-3 last:pb-5 even:bg-gray-50/70"
				>
					<div class="w-1/3 text-base text-gray-700">{{ d.label }}</div>
					<div class="w-2/3 text-base font-medium">{{ d.value }}</div>
				</div>
			</div>
		</div>
	</div>

	<AWSClusterNetworkOverview
		v-if="securityGroupInformation"
		:cluster="cluster"
		:clusterDoc="clusterDoc"
		:securityGroupInformation="securityGroupInformation"
	>
	</AWSClusterNetworkOverview>
</template>
<script>
import { h, defineAsyncComponent } from 'vue';
import { getCachedDocumentResource } from 'frappe-ui';
import { renderDialog } from '../../utils/components';
import { getDocResource } from '../../utils/resource';
import AWSClusterNetworkOverview from './AWSClusterNetworkOverview.vue';

export default {
	props: ['cluster'],
	components: {
		AWSClusterNetworkOverview
	},
	resources: {
		securityGroupInfo() {
			return {
				url: 'press.api.cluster.get_security_groups_information',
				params: {
					cluster: this.cluster
				},
				auto: true
			};
		}
	},
	computed: {
		clusterDoc() {
			return getCachedDocumentResource('Cluster', this.cluster);
		},
		clusterInformation() {
			return [
				{
					label: 'Cloud Provider',
					value: this.clusterDoc.doc.cloud_provider
				},
				{
					label: 'Region',
					value: this.clusterDoc.doc.region
				},
				{
					label: 'Availability Zone',
					value: this.clusterDoc.doc.availability_zone
				},
				{
					label: 'Owned by',
					value: this.clusterDoc.doc.team
				},
				{
					label: 'Created by',
					value: this.clusterDoc.doc.owner
				},
				{
					label: 'Created on',
					value: this.$format.date(this.clusterDoc.doc.creation)
				}
			];
		},
		securityGroupInformation() {
			return this.$resources.securityGroupInfo?.data;
		}
	}
};
</script>
