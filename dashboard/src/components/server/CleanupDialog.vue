<template>
	<Dialog
		:options="{
			title: title,
			size: '2xl',
		}"
		v-model="show"
	>
		<template #body-content>
			<div
				v-if="$resources?.cleanupSpaceEstimation?.loading"
				class="flex h-80 w-full items-center justify-center gap-2 text-base text-gray-700"
			>
				<Spinner class="w-4" /> Analyzing ...
			</div>

			<div
				v-else-if="$resources?.cleanupSpaceEstimation?.error"
				class="flex h-80 w-full items-center justify-center text-red-600"
			>
				Failed to fetch cleanup data.
			</div>
			<div v-else-if="parsedData" class="flex flex-col gap-4 text-gray-800">
				<AlertBanner
					title="Force cleanup is only allowed if the reclaimable space is more than or equal to 500MB."
					type="info"
					:showIcon="false"
					v-if="parsedData.total < 0.5"
				>
				</AlertBanner>
				<div class="rounded-md">
					<p>
						This action will <strong>permanently remove</strong> the following:
					</p>
					<ul class="list-disc ml-5 mt-3 space-y-2">
						<li>
							<strong>Archived folders</strong> — contain recently archived
							benches and sites.
						</li>
						<li>
							<strong>Docker images & containers</strong> — all unused Docker
							images and containers will be removed.
						</li>
						<li>
							<strong>Temporary files</strong> — cleanup will remove previously
							created temporary files.
						</li>
					</ul>

					<AlertBanner
						:title="`
                        <ul class=${'ml-2 space-y-1'}>
							<li>• Archived folders: ${parsedData.archived}</li>
							<li>• Docker images: ${parsedData.docker.images}</li>
							<li>• Docker containers: ${parsedData.docker.containers}</li>
						</ul>

						<div class=${'mt-3'}>
							<strong>Total reclaimable: ${parsedData.total}GB</strong>
						</div>
                        `"
						type="gray"
						:showIcon="false"
						class="mt-4"
					/>

					<AlertBanner
						title="
                        <ul>
							<li>
								• Sites and benches cannot be restored if archived by accident.
							</li>
							<li>
								• Benches cannot be restored once Docker images are cleaned.
							</li>
						</ul>
                        "
						type="error"
						:showIcon="true"
						class="mb-2 mt-2"
					/>

					<div v-if="parsedData.total >= 0.5">
						<Button
							variant="solid"
							iconLeft="trash-2"
							theme="red"
							@click="onCleanup()"
							class="w-full rounded"
						>
							Start Cleanup
						</Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script>
import { Spinner } from 'frappe-ui';
import { toast } from 'vue-sonner';

export default {
	name: 'CleanupDialog',
	components: {
		Spinner,
	},
	props: {
		title: {
			type: String,
			required: true,
		},
		server: {
			required: true,
		},
	},
	data() {
		return {
			show: true,
		};
	},
	mounted() {
		this.$resources.cleanupSpaceEstimation.submit();
	},
	resources: {
		cleanupSpaceEstimation() {
			return {
				url: 'press.api.server.get_reclaimable_size',
				makeParams: () => {
					return {
						name: this.server.doc.name,
					};
				},
				auto: false,
			};
		},
	},
	computed: {
		parsedData() {
			const raw = this.$resources.cleanupSpaceEstimation?.data;
			if (!raw) return null;
			return {
				archived: raw.archived ?? '0.0B',
				docker: {
					containers: raw.docker?.containers ?? '0.0B',
					images: raw.docker?.images ?? '0.0B',
				},
				total: raw.total ?? 0,
			};
		},
	},
	methods: {
		formatSize(valueInGB) {
			if (valueInGB > 1) return `${valueInGB.toFixed(2)}GB`;
			return `${(valueInGB * 1024).toFixed(2)}MB`;
		},
		onCleanup() {
			toast.promise(
				this.server.cleanup.submit({
					force: true,
				}),
				{
					loading: 'Starting cleanup...',
					success: () => {
						this.show = false;
						return 'Cleanup started';
					},
					error: (err) => {
						return 'Failed to start cleanup';
					},
				},
			);
		},
	},
};
</script>
