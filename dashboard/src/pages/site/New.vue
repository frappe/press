<script setup lang="ts">
import RadioGroup from '@/components/common/RadioGroup.vue';
import Step from '@/components/common/Step.vue';
import { Button } from 'frappe-ui';

import { ref } from 'vue';
const val = ref('individual');

const items = [
	{
		title: 'Individual site',
		value: 'individual',
		desc: 'Start small and run a single site with multiple apps on shared server',
		price: '5',
		icon: LucidePanelTopInactive,
	},

	{
		title: 'On my own server',
		value: 'own server',
		desc: 'Get a virtual machine to host multiple sites and benches',
		price: '5',
		icon: LucideServer,
	},
	{
		title: 'Dedicated server',
		value: 'dedicated server',
		desc: 'Get a dedicated server to host your site and bench',
		price: '5',
		icon: LucideServer,
		disabled: true,
	},
];
</script>

<template>
	<div class="p-5 flex flex-col">
		<span class="font-semibold text-ink-gray-6 mb-5">
			Create your new site</span
		>

		<Step label="1" class="flex flex-col gap-4">
			<div class="flex items-center justify-between">
				<span class="font-semibold text-ink-gray-7"
					>How do you want to host your new site?</span
				>

				<Button variant="ghost" class="text-ink-gray-6">
					<template #prefix>
						<LucideHelpCircle class="size-4" />
					</template>
					Help me choose</Button
				>
			</div>

			<RadioGroup
				v-model="val"
				:items
				class="grid grid-cols-3 gap-4 mb-10"
				itemClass="p-4 flex gap-2 text-sm leading-normal"
			>
				<template #item="{ item }" class="kekw">
					<div class="flex flex-col text-left gap-1">
						<span class="text-base font-semibold">{{ item.title }}</span>
						<p class="text-ink-gray-6">{{ item.desc }}</p>
						<span class="mt-1"
							>${{ item.price }} <span class="text-gray-500">/ mo onwards</span>
						</span>
					</div>

					<div
						class="flex items-center gap-2 p-2 bg-surface-gray-2 mb-auto rounded text-ink-gray-6"
					>
						<component :is="item.icon" class="size-4" />
					</div>
				</template>
			</RadioGroup>
		</Step>

		<Step label="2">
			<span class="font-semibold text-ink-gray-6">
				Select a server hosting provider</span
			>

			<span class="text-ink-gray-5"> Select a provider </span>

			<div></div>
		</Step>
	</div>
</template>
