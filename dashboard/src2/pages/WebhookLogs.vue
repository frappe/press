<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div class="flex items-center space-x-2">
			<Breadcrumbs
				:items="[
					{
						label: 'Webhook Logs',
						route: '/webhook/' + this.$route.params.id + '/logs'
					}
				]"
			/>
		</div>
	</Header>
	<ObjectList :options="options" class="mt-2 px-5" />
	<WebhookLogDetails
		:id="selectedWebhookLogId"
		v-if="showWebhookLogDetails"
		v-model="showWebhookLogDetails"
	/>
</template>
<script>
import { Breadcrumbs, Badge } from 'frappe-ui';
import Header from '../components/Header.vue';
import ObjectList from '../components/ObjectList.vue';
import { h } from 'vue';
import WebhookLogDetails from '../components/settings/WebhookLogDetails.vue';

export default {
	name: 'WebhookLogs',
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		WebhookLogDetails
	},
	data() {
		return {
			showWebhookLogDetails: false,
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
						webhook: this.$route.params.id
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
		options() {
			return {
				data: () => this.$resources?.logs?.data || [],
				columns: [
					{
						label: 'Event',
						fieldname: 'event',
						width: 0.2
					},
					{
						label: 'Endpoint',
						fieldname: 'endpoint',
						width: 0.5
					},
					{
						label: 'Status',
						fieldname: 'status',
						width: 0.1,
						format: _ => '',
						prefix(row) {
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
						width: 0.2,
						format(value) {
							return new Date(value).toLocaleString();
						}
					}
				],
				rowActions: ({ row }) => {
					return [
						{
							label: 'View',
							onClick: () => {
								this.selectedWebhookLogId = row.name;
								this.showWebhookLogDetails = true;
							}
						}
					];
				}
			};
		}
	}
};
</script>
