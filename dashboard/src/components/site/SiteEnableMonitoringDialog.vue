<template>
	<Dialog
		:options="{
			title: 'Monitoring & Alerts are Disabled',
			size: '2xl',
		}"
		v-model="showDialog"
	>
		<template #body-content>
			<div
				v-if="$resources.siteResource.loading"
				class="flex w-full items-center justify-center gap-2 py-20 text-gray-700"
			>
				<Spinner class="w-4" /> Loading data...
			</div>
			<div v-else-if="siteDoc?.is_monitoring_disabled" class="w-full">
				<p class="mb-2 text-gray-800 text-base font-medium">
					Cause of disabling monitoring :
				</p>
				<div
					class="rounded border bg-gray-50 p-2 text-base font-normalprose prose-sm space-y-2 whitespace-break-spaces w-ful"
				>
					{{ siteDoc.reason_for_disabling_monitoring || 'Unknown Reason' }}
				</div>

				<!-- Result -->
				<div
					v-if="enabledMonitoring === false"
					class="flex flex-col gap-2 mt-4 w-full"
				>
					<AlertBanner
						type="error"
						:showIcon="true"
						title="Failed to enable monitoring"
					/>
					<p class="mt-1 text-gray-800 text-base font-medium">Reason -</p>
					<div
						class="rounded border bg-gray-50 p-2 text-base font-normalprose prose-sm space-y-2 whitespace-break-spaces w-full"
						style="line-height: inherit"
					>
						{{ reasonForFailureInEnablingMonitoring }}
					</div>
					<p class="mt-1 text-gray-800 text-base font-medium">
						Possible Solution -
					</p>
					<div
						class="rounded border bg-gray-50 p-2 text-base font-normalprose prose-sm space-y-2 whitespace-break-spaces w-full"
						style="line-height: inherit"
					>
						{{ solutionToResolveIssue }}
					</div>
				</div>

				<Button
					variant="solid"
					class="w-full mt-4"
					:loading="$resources.enableMonitoring?.loading"
					@click="$resources.enableMonitoring?.submit"
				>
					Check & Enable Monitoring
				</Button>
			</div>
			<div v-else>
				Monitoring is enabled already. No action is required from your end.
			</div>
		</template>
	</Dialog>
</template>
<script>
import AlertBanner from '../AlertBanner.vue';
import { toast } from 'vue-sonner';

export default {
	name: 'SiteEnableMonitoringDialog',
	props: {
		site: {
			type: String,
			required: true,
		},
	},
	components: {
		AlertBanner,
	},
	data() {
		return {
			showDialog: true,
			enabledMonitoring: null,
			reasonForFailureInEnablingMonitoring: '',
			solutionToResolveIssue: '',
		};
	},
	resources: {
		siteResource() {
			return {
				type: 'document',
				doctype: 'Site',
				name: this.site,
				auto: true,
			};
		},
		enableMonitoring() {
			return {
				url: 'press.api.client.run_doc_method',
				makeParams() {
					return {
						dt: 'Site',
						dn: this.site,
						method: 'enable_monitoring',
					};
				},
				auto: false,
				onSuccess: (e) => {
					if (e?.message) {
						this.enabledMonitoring = e?.message?.enabled ?? null;
						this.reasonForFailureInEnablingMonitoring =
							e?.message?.reason ?? '';
						this.solutionToResolveIssue = e?.message?.solution ?? '';

						if (this.enabledMonitoring) {
							toast.success('Monitoring enabled successfully');
							this.hide();
						} else {
							toast.error('Failed to enable monitoring');
						}
					}
				},
			};
		},
	},
	computed: {
		siteDoc() {
			return this.$resources?.siteResource?.doc ?? {};
		},
	},
	methods: {
		hide() {
			this.showDialog = false;
		},
	},
};
</script>
