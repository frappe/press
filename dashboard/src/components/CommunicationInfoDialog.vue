<template>
	<Dialog
		:options="{ title: 'Notification Configuration', size: '3xl' }"
		v-model="showDialog"
	>
		<template #body-content>
			<div class="flex flex-col w-full">
				<AlertBanner
					v-if="referenceDoctype === 'Team'"
					title="Notifications will go to the General channel by default. If General isn't available, they'll be delivered to registered email addresses."
					type="info"
					:showIcon="false"
					class="mb-3"
				/>

				<AlertBanner
					v-else
					title="Notifications will go to the General channel by default. If General isn't available, they'll be delivered through team-level channels."
					type="info"
					:showIcon="false"
					class="mb-3"
				/>

				<div class="flex justify-end gap-2">
					<Button
						variant="solid"
						class="mb-3"
						iconLeft="plus"
						@click="
							currentCommunicationInfos.push({
								channel: 'Email',
								type: 'General',
								value: '',
							})
						"
					>
						New
					</Button>
					<Button
						variant="subtle"
						class="mb-3"
						icon="refresh-cw"
						:loading="$resources.getCommunicationInfos.loading"
						@click="$resources.getCommunicationInfos.submit"
					>
						Refresh
					</Button>
				</div>
				<div
					v-if="$resources.getCommunicationInfos.loading"
					class="flex w-full items-center justify-center gap-2 py-20 text-gray-700"
				>
					<Spinner class="w-4" /> Loading data...
				</div>
				<div v-else>
					<GenericList class="w-100" :options="communicationInfosListOptions" />
					<ErrorMessage
						class="mt-2"
						:message="$resources.updateCommunicationInfos.error"
					/>
					<Button
						variant="solid"
						class="w-full mt-5"
						@click="$resources?.updateCommunicationInfos?.submit"
						:loading="$resources?.updateCommunicationInfos?.loading"
						>Update Settings</Button
					>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { h } from 'vue';
import { Select, TextInput } from 'frappe-ui';
import GenericList from './GenericList.vue';
import AlertBanner from './AlertBanner.vue';

export default {
	name: 'CommunicationInfoDialog',
	props: {
		referenceDoctype: {
			type: String,
			validator: (value) => ['Team', 'Site', 'Server'].includes(value),
			required: true,
		},
		referenceName: {
			type: String,
			required: true,
		},
	},
	emits: ['close'],
	components: {
		GenericList,
		Select,
		TextInput,
		AlertBanner,
	},
	data() {
		return {
			showDialog: true,
			currentCommunicationInfos: [],
		};
	},
	mounted() {
		if (this.referenceDoctype && this.referenceName) {
			this.$resources.getCommunicationInfos.submit();
		}
	},
	resources: {
		getCommunicationInfos() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: this.referenceDoctype,
						dn: this.referenceName,
						method: 'get_communication_infos',
					};
				},
				onSuccess: (data) => {
					this.currentCommunicationInfos = data.message || [];
				},
				auto: false,
			};
		},
		updateCommunicationInfos() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: this.referenceDoctype,
						dn: this.referenceName,
						method: 'update_communication_infos',
						args: { values: this.currentCommunicationInfos },
					};
				},
				auto: false,
				onSuccess: () => {
					this.$toast.success('Notification settings updated');
					this.hide();
				},
			};
		},
	},
	computed: {
		communicationInfosListOptions() {
			return {
				data: this.currentCommunicationInfos,
				columns: [
					{
						fieldname: 'type',
						label: 'Type',
						width: '2fr',
						type: 'Component',
						component_width: '100%',
						component: ({ row }) => {
							return h(
								'div',
								{
									class: 'w-full',
								},
								[
									h(Select, {
										style: { width: '100%' },
										options: this.filteredCommunicationTypes.map((type) => ({
											label: type,
											value: type,
										})),
										modelValue: row.type,
										'onUpdate:modelValue': (value) => {
											row.type = value;
										},
									}),
								],
							);
						},
					},
					{
						fieldname: 'channel',
						label: 'Channel',
						width: '2fr',
						type: 'Component',
						component: ({ row }) => {
							return h(
								'div',
								{
									class: 'w-full',
								},
								[
									h(Select, {
										options:
											row.type == 'Incident'
												? [
														{
															label: 'Email',
															value: 'Email',
														},
														{
															label: 'Phone Call',
															value: 'Phone Call',
														},
													]
												: [
														{
															label: 'Email',
															value: 'Email',
														},
													],
										modelValue: row.channel,
										'onUpdate:modelValue': (value) => {
											row.channel = value;
										},
									}),
								],
							);
						},
					},
					{
						fieldname: 'value',
						label: 'Email / Phone No',
						width: '5fr',
						type: 'Component',
						component({ row }) {
							return h(TextInput, {
								class: 'w-full',
								modelValue: row.value,
								'onUpdate:modelValue': (value) => {
									row.value = value;
								},
							});
						},
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						width: '0.5fr',
						Button: ({ row }) => {
							return {
								label: 'Remove',
								variant: 'subtle',
								icon: 'x',
								// theme: 'red',
								onClick: () => {
									this.removeCommunicationInfo(row);
								},
							};
						},
					},
				],
			};
		},
		filteredCommunicationInfos() {
			return this.currentCommunicationInfos.filter(
				(info) => info.channel && info.type && info.value,
			);
		},
		filteredCommunicationTypes() {
			if (this.referenceDoctype == 'Server') {
				return ['General', 'Incident', 'Server Activity'];
			} else if (this.referenceDoctype == 'Site') {
				return ['General', 'Site Activity'];
			}
			return [
				'General',
				'Billing',
				'Incident',
				'Server Activity',
				'Site Activity',
				'Marketplace',
			];
		},
	},
	methods: {
		refreshCommunicationInfos() {
			this.$resources.getCommunicationInfos.submit();
		},
		removeCommunicationInfo(row) {
			this.currentCommunicationInfos = this.currentCommunicationInfos.filter(
				(info) =>
					!(
						info.channel === row.channel &&
						info.type === row.type &&
						info.value === row.value
					),
			);
		},
		hide() {
			this.showDialog = false;
			this.$emit('close');
		},
	},
};
</script>
