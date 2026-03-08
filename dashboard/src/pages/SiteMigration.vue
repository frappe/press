<template>
	<div class="p-5">
		<div v-if="errors" class="flex flex-col gap-2">
			<AlertAddressableError
				v-for="error in errors"
				class="mb-5"
				:name="error.name"
				:title="error.title"
				@done="$resources.siteAction.reload()"
			/>
		</div>

		<Button :route="{ name: 'Site Detail Migrations' }">
			<template #prefix>
				<lucide-arrow-left class="inline-block h-4 w-4" />
			</template>
			All Migrations
		</Button>

		<div class="mt-3">
			<div class="flex w-full items-center">
				<h2 class="text-lg font-medium text-gray-900">
					{{ siteAction.action_type }}
				</h2>
				<Badge class="ml-2" :label="siteAction.status" />
				<div class="ml-auto space-x-2">
					<Button
						@click="$resources.siteAction.reload()"
						:loading="$resources.siteAction.loading"
					>
						<template #icon>
							<lucide-refresh-ccw class="h-4 w-4" />
						</template>
					</Button>
					<Dropdown :options="dropdownOptions">
						<template v-slot="{ open }">
							<Button>
								<template #icon>
									<lucide-more-horizontal class="h-4 w-4" />
								</template>
							</Button>
						</template>
					</Dropdown>
				</div>
			</div>
			<div>
				<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-7">
					<div>
						<div class="text-sm font-medium text-gray-500">
							Destination Bench
						</div>
						<div
							class="mt-2 text-sm text-ink-blue-3 font-medium"
							@click="openDestinationBenchPage"
							v-if="destinationReleaseGroupName"
							style="cursor: pointer"
						>
							{{ destinationReleaseGroupName || '-'
							}}<span>&#8599;&#65038;</span>
						</div>
						<div class="mt-2 text-sm text-gray-900" v-else>-</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">
							Destination Server
						</div>
						<div
							class="mt-2 text-sm text-ink-blue-3 font-medium"
							@click="openDestinationServerPage"
							v-if="destinationServerName"
							style="cursor: pointer"
						>
							{{ destinationServerName || '-' }}<span>&#8599;&#65038;</span>
						</div>
						<div class="mt-2 text-sm text-gray-900" v-else>-</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">Creation</div>
						<div class="mt-2 text-sm text-gray-900">
							{{ $format.date(siteAction.creation, 'lll') }}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">Creator</div>
						<div class="mt-2 text-sm text-gray-900">
							{{ siteAction.owner }}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">Duration</div>
						<div class="mt-2 text-sm text-gray-900">
							{{
								siteAction.duration
									? this.format_seconds(siteAction.duration)
									: '-'
							}}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">Start</div>
						<div class="mt-2 text-sm text-gray-900">
							{{
								siteAction.start ? $format.date(siteAction.start, 'lll') : '-'
							}}
						</div>
					</div>
					<div>
						<div class="text-sm font-medium text-gray-500">End</div>
						<div class="mt-2 text-sm text-gray-900">
							{{ siteAction.end ? $format.date(siteAction.end, 'lll') : '-' }}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Build Steps -->
		<div class="mt-8 space-y-4">
			<JobStep v-for="step in steps" :step="step" :key="step.name" />
		</div>
	</div>
</template>
<script>
import { createResource } from 'frappe-ui';
import { toast } from 'vue-sonner';
import JobStep from '../components/JobStep.vue';
import AlertAddressableError from '../components/AlertAddressableError.vue';
import AlertBanner from '../components/AlertBanner.vue';

export default {
	name: 'SiteAction',
	props: ['id'],
	components: {
		JobStep,
		AlertBanner,
		AlertAddressableError,
	},
	resources: {
		siteAction() {
			if (!this.id) return;
			return {
				type: 'document',
				doctype: 'Site Action',
				name: this.id,
				auto: true,
				transform: (record) => {
					record.steps = record.steps.map((step) => {
						return {
							name: step.name,
							title: step.title ? `${step.stage} - ${step.title}` : step.stage,
							output: step.output || 'No Output',
							status: step.status,
							isOpen: false,
						};
					});
				},
				onSuccess: (data) => {
					if (
						!['Success', 'Failure', 'Recovered', 'Fatal'].includes(data.status)
					) {
						setTimeout(() => {
							this.$resources.siteAction.reload();
						}, 5000);
					}
				},
			};
		},
	},
	computed: {
		siteAction() {
			return this.$resources.siteAction?.doc ?? {};
		},
		steps() {
			return this.$resources.siteAction?.doc?.steps || [];
		},
		errors() {
			return this.$resources.siteAction?.doc?.errors || [];
		},
		dropdownOptions() {
			return [
				{
					label: 'View in Desk',
					icon: 'external-link',
					condition: () => this.$team.doc?.is_desk_user,
					onClick: () => {
						window.open(
							`${window.location.protocol}//${window.location.host}/app/site-action/${this.id}`,
							'_blank',
						);
					},
				},
				{
					label: 'Start Now',
					icon: 'play',
					condition: () => this.siteAction?.status === 'Scheduled',
					onClick: () => {
						let startNowAction = createResource({
							url: 'press.api.client.run_doc_method',
							makeParams: () => {
								return {
									dt: 'Site Action',
									dn: this.siteAction.name,
									method: 'start_now',
								};
							},
						});

						toast.promise(startNowAction.submit(), {
							loading: 'Starting migration...',
							success: () => {
								this.$resources.siteAction.reload();
								return 'Site migration started';
							},
							error: 'Failed to start migration',
						});
					},
				},
				{
					label: 'Cancel',
					icon: 'x',
					condition: () => this.siteAction?.status === 'Scheduled',
					onClick: () => {
						let cancelAction = createResource({
							url: 'press.api.client.run_doc_method',
							makeParams: () => {
								return {
									dt: 'Site Action',
									dn: this.siteAction.name,
									method: 'cancel_action',
								};
							},
						});

						toast.promise(cancelAction.submit(), {
							loading: 'Cancelling migration...',
							success: () => {
								this.$resources.siteAction.reload();
								return 'Site migration cancelled';
							},
							error: 'Failed to cancel migration',
						});
					},
				},
			].filter((option) => option.condition?.() ?? true);
		},
		destinationServerName() {
			let server_name = this.siteAction.arguments_dict?.destination_server;
			if (!server_name) return null;
			try {
				return server_name.split('.')[0];
			} catch (e) {
				console.error('Error parsing destination server:', e);
				return null;
			}
		},
		destinationServerFullName() {
			return this.siteAction.arguments_dict?.destination_server;
		},
		destinationReleaseGroupName() {
			return this.siteAction.arguments_dict?.destination_release_group;
		},
	},
	methods: {
		format_seconds(seconds) {
			if (seconds === null) {
				return '-';
			}
			if (seconds < 60) {
				return `${Math.ceil(seconds)}s`;
			}
			const minutes = Math.floor(seconds / 60);
			const remainingSeconds = Math.ceil(seconds % 60);
			return `${minutes}m ${remainingSeconds}s`;
		},
		openDestinationServerPage() {
			if (this.destinationServerFullName) {
				const route = this.$router.resolve({
					name: 'Server Detail',
					params: { name: this.destinationServerFullName },
				});
				window.open(route.href, '_blank');
			}
		},
		openDestinationBenchPage() {
			if (this.destinationReleaseGroupName) {
				const route = this.$router.resolve({
					name: 'Release Group Detail',
					params: { name: this.destinationReleaseGroupName },
				});
				window.open(route.href, '_blank');
			}
		},
	},
};
</script>
