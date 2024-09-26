<template>
	<Dialog
		:options="{
			title: selectedWebhookAttemptId
				? `Webhook Attempt - ${selectedWebhookAttemptId}`
				: 'Webhook Attempts',
			size: '4xl'
		}"
	>
		<template #body-content>
			<p class="text-sm mb-2 text-gray-700" v-if="!selectedWebhookAttemptId">
				<strong>Note:</strong> You can only view logs of last 24 hours
			</p>
			<ObjectList :options="listOptions" v-if="!selectedWebhookAttemptId" />
			<Button
				class="mb-2"
				iconLeft="arrow-left"
				v-if="selectedWebhookAttemptId"
				@click="selectedWebhookAttemptId = null"
			>
				Back
			</Button>
			<WebhookAttemptDetails
				:id="selectedWebhookAttemptId"
				v-if="selectedWebhookAttemptId"
			/>
		</template>
	</Dialog>
</template>
<script>
import { Breadcrumbs, Badge } from 'frappe-ui';
import Header from '../Header.vue';
import ObjectList from '../ObjectList.vue';
import { h } from 'vue';
import WebhookAttemptDetails from './WebhookAttemptDetails.vue';

export default {
	name: 'WebhookAttempts',
	props: ['name'],
	components: {
		Header,
		Breadcrumbs,
		ObjectList,
		WebhookAttemptDetails
	},
	data() {
		return {
			selectedWebhookAttemptId: null
		};
	},
	resources: {
		attempts() {
			return {
				url: 'press.api.webhook.attempts',
				params: {
					webhook: this.$props.name
				},
				inititalData: [],
				auto: true
			};
		}
	},
	computed: {
		listOptions() {
			return {
				data: () => this.$resources?.attempts?.data || [],
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
						format: val => {
							if (!val || parseInt(val) === 0) return '-';
							return val;
						},
						align: 'center'
					},
					{
						label: 'Timestamp',
						fieldname: 'timestamp',
						width: 0.3,
						format(value) {
							return new Date(value).toLocaleString();
						}
					}
				],
				onRowClick: row => {
					this.selectedWebhookAttemptId = row.name;
				}
			};
		}
	}
};
</script>
