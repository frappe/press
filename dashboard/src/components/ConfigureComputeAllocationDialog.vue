<script setup lang="ts">
import { getCachedDocumentResource, Switch } from 'frappe-ui';
import { computed, getCurrentInstance, ref, watch } from 'vue';

const { appContext } = getCurrentInstance()!;
const $toast = appContext.config.globalProperties.$toast;
const props = defineProps<{ site: string }>();
const site = getCachedDocumentResource('Site', props.site);

const open = ref(true);
const switchValue = ref(false);

const isHighPerformanceEnabled = computed(() => {
	const sitePlanName = site.doc.current_plan.name?.toLowerCase();
	return !sitePlanName?.includes('low');
});

watch(
	isHighPerformanceEnabled,
	(val) => {
		switchValue.value = val;
	},
	{ immediate: true },
);

const LOW_PERFORMANCE_PLAN_PREFIX = 'Unlimited - Low';
const HIGH_PERFORMANCE_PLAN_PREFIX = 'Unlimited';

const nextSitePlanName = computed(() => {
	if (isHighPerformanceEnabled.value) {
		return site.doc.current_plan.name?.replace(
			HIGH_PERFORMANCE_PLAN_PREFIX,
			LOW_PERFORMANCE_PLAN_PREFIX,
		);
	} else {
		return site.doc.current_plan.name?.replace(
			LOW_PERFORMANCE_PLAN_PREFIX,
			HIGH_PERFORMANCE_PLAN_PREFIX,
		);
	}
});

function onClickSave() {
	$toast.promise(site.setPlan.submit({ plan: nextSitePlanName }), {
		loading: 'Reconfiguring bench workers...',
		success: 'Performance has been reconfigured',
		error: 'Failed to configure performance',
	});
}
</script>

<template>
	<Dialog
		:options="{
			title: 'Configure compute allocation',
			size: 'xl',
		}"
		v-model="open"
	>
		<template #body-content>
			<div class="flex flex-col gap-7 text-base">
				<div class="flex w-full space-x-4">
					<div class="flex flex-col flex-grow space-y-3">
						<p class="font-semibold">Enable higher compute allocation</p>
						<p class="text-ink-gray-6 leading-normal">
							Maximize computing power for this site, or share resources equally
							with sites on this server.
						</p>
					</div>
					<Switch v-model="switchValue" size="md" class="px-4" />
				</div>

				<div class="flex w-full">
					<div class="flex-grow">
						<Button variant="ghost">
							<template #prefix>
								<LucideHelpCircle class="size-4" />
							</template>
							Learn More
						</Button>
					</div>

					<div class="flex gap-3">
						<Button @click="open = false">Cancel</Button>
						<Button
							:loading="site.setPlan.loading"
							:disabled="switchValue === isHighPerformanceEnabled"
							variant="solid"
							@click="onClickSave"
							>Save changes</Button
						>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
