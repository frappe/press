<template>
	<Dialog
		:options="{
			title: 'Auto Scale Triggers',
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$resources.configuredAutoscales.loading"
				class="flex w-full items-center justify-center gap-2 py-32 text-gray-700"
			>
				<Spinner class="w-4" /> Loading
			</div>
			<div v-else>
				<ObjectList :options="autoScaleTriggerOptions" ref="list" />
			</div>
		</template>
	</Dialog>
</template>

<script>
import { getCachedDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import { confirmDialog } from '../../utils/components';
import ObjectList from '../ObjectList.vue';

export default {
	name: 'AutoScale',
	props: {
		name: {
			type: String,
			required: true,
		},
	},
	components: { ObjectList },
	data() {
		return { show: true };
	},
	resources: {
		configuredAutoscales() {
			return {
				url: 'press.api.server.get_configured_autoscale_triggers',
				params: { name: this.name },
				auto: true,
				initialData: [],
			};
		},
	},

	computed: {
		server() {
			return getCachedDocumentResource('Server', this.name);
		},
		autoScaleTriggerOptions() {
			return {
				data: () => {
					return this.$resources.configuredAutoscales.data || [];
				},
				columns: [
					{ label: 'Metric', fieldname: 'metric' },
					{
						label: 'Threshold',
						fieldname: 'threshold',
						class: 'text-gray-600',
						align: 'left',
						format(value) {
							return `${value}%`;
						},
					},
					{
						label: 'Action',
						fieldname: 'action',
					},
				],
				showTooltip: false,
				selectable: false,
				emptyState: {
					title: 'No Autoscale Triggers found',
					description: 'Your have not configured any auto scale triggers yet',
				},
				actions: () => [
					{
						variant: 'solid',
						theme: 'red',
						label: 'Remove Triggers',
						disabled: this.$resources?.configuredAutoscales?.data.length === 0,
						onClick: () => {
							toast.promise(
								this.server.removeAutomatedScalingTriggers.submit(),
								{
									loading: 'Removing triggers...',
									success: () => {
										this.show = false;
										return 'Removed Triggers';
									},
									error: () =>
										getToastErrorMessage(
											this.server.removeAutomatedScalingTriggers.error ||
												'Failed to remove triggers',
										),
									duration: 5000,
								},
							);
						},
					},
					{
						variant: 'solid',
						label:
							this.$resources?.configuredAutoscales?.data.length === 0
								? 'Add Triggers'
								: 'Update Triggers',
						onClick: () => {
							this.show = false;
							const server = this.server;

							confirmDialog({
								title: 'Configure Automated Scaling',
								message: `
							You can configure when your server scales up and down depending on CPU loads.<br>
							refer to this documentation to learn more!
						`,
								fields: [
									{
										label: 'Enter the new threshold load to scale up at',
										fieldname: 'scaleUpCPUThreshold',
										type: 'float',
									},
									{
										label: 'Enter the new threshold load to scale down at',
										fieldname: 'scaleDownCPUThreshold',
										type: 'float',
									},
								],
								primaryAction: {
									label: 'Configure Automated Scaling',
								},
								onSuccess({ hide, values }) {
									if (!server || server.addAutomatedScalingTriggers.loading)
										return;
									let upThreshold = parseFloat(values.scaleUpCPUThreshold);
									let downThreshold = parseFloat(values.scaleDownCPUThreshold);

									if (!upThreshold || !downThreshold) {
										toast.error(
											'Invalid values for scale up or down threshold',
										);
										return;
									}

									toast.promise(
										server.addAutomatedScalingTriggers.submit(
											{
												scale_up_cpu_threshold: upThreshold,
												scale_down_cpu_threshold: downThreshold,
											},
											{
												onSuccess() {
													hide();
												},
											},
										),
										{
											loading: 'Adding triggers...',
											success: 'Added triggers',
											error: () =>
												getToastErrorMessage(
													server.addAutomatedScalingTriggers.error ||
														'Failed to add triggers',
												),
											duration: 5000,
										},
									);
								},
							});
						},
					},
				],
			};
		},
	},
};
</script>
