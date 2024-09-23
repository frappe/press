<template>
	<Dialog
		:options="{
			title: selectedWebhookLogId
				? `Webhook Log - ${selectedWebhookLogId}`
				: 'Webhook Logs',
			size: '4xl'
		}"
	>
		<template #body-content>
			<p class="text-sm mb-2 text-gray-700" v-if="!selectedWebhookLogId">
				<strong>Note:</strong> You can only view logs of last 24 hours
			</p>
			<ObjectList :options="listOptions" v-if="!selectedWebhookLogId" />
			<Button
				class="mb-2"
				iconLeft="arrow-left"
				v-if="selectedWebhookLogId"
				@click="selectedWebhookLogId = null"
			>
				Back
			</Button>
			<WebhookLogDetails
				:id="selectedWebhookLogId"
				v-if="selectedWebhookLogId"
			/>
		</template>
	</Dialog>
</template>
<script>
import { Breadcrumbs, Badge } from 'frappe-ui';
import Header from '../Header.vue';
import ObjectList from '../ObjectList.vue';
import { h } from 'vue';
import WebhookLogDetails from '../settings/WebhookLogDetails.vue';

export default {
	name: 'WebhookLogs',
	props: ['name'],
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		WebhookLogDetails
	},
	data() {
		return {
			selectedWebhookLogId: null
		};
	},
	resources: {
		logs() {
			return {
				url: 'press.api.client.get_list',
				params: {
					doctype: 'Press Webhook Log',
					filters: {
						webhook: this.$props.name
					},
					fields: [
						'name',
						'event',
						'endpoint',
						'status',
						'response_status_code',
						'creation'
					],
					order_by: 'creation desc',
					page_length: 20
				},
				inititalData: [],
				auto: true
			};
		}
	},
	computed: {
		listOptions() {
			return {
				data: () => this.$resources?.logs?.data || [],
				columns: [
					{
						label: 'Event',
						fieldname: 'event',
						width: 0.25
					},
					{
						label: 'Endpoint',
						fieldname: 'endpoint',
						width: 0.5,
						format: value => value.substring(0, 50)
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: 0.1,
						type: 'Component',
						component({ row }) {
							return row.status === 'Sent'
								? h(Badge, {
										label: row.status,
										theme: 'green'
								  })
								: h(Badge, {
										label: row.status,
										theme: 'red'
								  });
						}
					},
					{
						label: 'Code',
						fieldname: 'response_status_code',
						width: 0.1,
						format: val => val || '-'
					},
					{
						label: 'Timestamp',
						fieldname: 'creation',
						width: 0.3,
						format(value) {
							return new Date(value).toLocaleString();
						}
					}
				],
				onRowClick: row => {
					this.selectedWebhookLogId = row.name;
				}
			};
		}
	}
};
</script>
