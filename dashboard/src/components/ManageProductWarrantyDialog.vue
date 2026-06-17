<script setup lang="ts">
import { getCachedDocumentResource, Switch } from 'frappe-ui'
import { computed, getCurrentInstance, ref, watch } from 'vue'
import dayjs from '../utils/dayjs'

const { appContext } = getCurrentInstance()!
const $toast = appContext.config.globalProperties.$toast
const props = defineProps<{ site: string }>()
const site = getCachedDocumentResource('Site', props.site)

const open = ref(true)
const switchValue = ref(false)

const isSupportEnabled = computed(() => {
	const sitePlan = site.doc?.current_plan
	return (
		!!sitePlan?.support_included && sitePlan?.name?.includes(' - Supported')
	)
})

watch(
	isSupportEnabled,
	(val) => {
		switchValue.value = val
	},
	{ immediate: true },
)

const LOW_PERFORMANCE_PLAN_PREFIX = 'Unlimited - Low'
const HIGH_PERFORMANCE_PLAN_PREFIX = 'Unlimited'
const SUPPORTED_PLAN_CLAUSE = ' - Supported'
const UNSUPPORTED_PLAN_CLAUSE = ''

const nextSitePlanName = computed(() => {
	const planName = site.doc?.current_plan?.name as string

	if (planName.includes(' - Supported') && isSupportEnabled.value) {
		return site.doc.current_plan.name?.replace(
			SUPPORTED_PLAN_CLAUSE,
			UNSUPPORTED_PLAN_CLAUSE,
		)
	} else {
		// assuming format for supported plan is: {PERFORMANCE_PLAN_PREFIX} - {SUPPORT_CLAUSE} - {CLOUD_PROVIDER (optional)}
		if (planName.includes(LOW_PERFORMANCE_PLAN_PREFIX)) {
			return planName.replace(
				LOW_PERFORMANCE_PLAN_PREFIX,
				`${LOW_PERFORMANCE_PLAN_PREFIX}${SUPPORTED_PLAN_CLAUSE}`,
			)
		} else if (planName.includes(HIGH_PERFORMANCE_PLAN_PREFIX)) {
			return planName.replace(
				HIGH_PERFORMANCE_PLAN_PREFIX,
				`${HIGH_PERFORMANCE_PLAN_PREFIX}${SUPPORTED_PLAN_CLAUSE}`,
			)
		}
	}
})

const nextChangeAvailableOn = computed(() => {
	const nextDate = dayjs(
		site.doc?.next_allowed_dedicated_product_warranty_change_date,
	)
	if (dayjs().isAfter(nextDate)) {
		return 'Available Now'
	} else {
		return nextDate.format('D MMM YYYY, h:mm a')
	}
})

const disablePrimaryAction = computed(
	() =>
		switchValue.value === isSupportEnabled.value ||
		nextChangeAvailableOn.value !== 'Available Now',
)

function onClickSave() {
	$toast.promise(site.setPlan.submit({ plan: nextSitePlanName.value }), {
		loading: 'Changing product warranty...',
		success: 'Product warranty changed successfully',
		error: 'Failed to change product warranty',
	})
}
</script>

<template>
	<Dialog
		:options="{
			title: 'Manage Product Warranty',
			size: 'xl',
		}"
		v-model="open"
	>
		<template #body-content>
			<div class="flex flex-col gap-4 text-base">
				<div class="flex w-full space-x-4">
					<div class="flex flex-col flex-grow space-y-3">
						<p class="font-semibold">Enable product warranty</p>
						<p class="text-ink-gray-6 leading-normal">
							Get support for issues with Frappe apps, not functional queries
						</p>
					</div>
					<Switch
						v-model="switchValue"
						size="md"
						class="px-4"
						:disabled="nextChangeAvailableOn !== 'Available Now' || (site.doc?.dedicated_server_warranty_limit?.available <= 0 && !isSupportEnabled)"
					/>
				</div>

				<hr />

				<div class="flex flex-col gap-2 w-full">
					<div class="flex">
						<p class="flex-grow text-ink-gray-6">
							Warranty limit for this server
						</p>
						<p
							v-if="!site.doc?.dedicated_server_warranty_limit?.total"
							class="text-ink-gray-4 font-normal"
						>
							Not Applicable
						</p>
						<p
							v-else-if="site.doc?.dedicated_server_warranty_limit?.available <= 0"
							class="text-ink-red-4"
						>
							{{ site.doc?.dedicated_server_warranty_limit?.available < 0 ? "Exceeded" : "Reached" }}
							({{ site.doc?.dedicated_server_warranty_limit?.consumed }}
							/
							{{ site.doc?.dedicated_server_warranty_limit?.total }}
							sites)
						</p>
						<p v-else>
							{{ site.doc?.dedicated_server_warranty_limit?.consumed }}
							/
							{{ site.doc?.dedicated_server_warranty_limit?.total }}
							sites
						</p>
					</div>
					<div class="flex">
						<p class="flex-grow text-ink-gray-6">Next change available after</p>
						<p
							:class="
								nextChangeAvailableOn === 'Available Now'
									? 'text-ink-green-3 font-medium'
									: ''
							"
						>
							{{ nextChangeAvailableOn }}
						</p>
					</div>
				</div>

				<div class="flex w-full">
					<a
						class="flex-grow"
						href="https://docs.frappe.io/cloud/getting-started/plans-pricing/change-product-warranty-for-dedicated-sites"
						target="_blank"
					>
						<Button variant="ghost">
							<template #prefix>
								<LucideHelpCircle class="size-4" />
							</template>
							Learn More
						</Button>
					</a>

					<div class="flex gap-3">
						<Button @click="open = false">Cancel</Button>
						<Button
							:loading="site.setPlan.loading"
							:disabled="disablePrimaryAction"
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
