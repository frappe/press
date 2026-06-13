<script setup>
import Points1Icon from '@/components/icons/Points-1.vue'
import People1Icon from '@/components/icons/People-1.vue'
import MoneyIcon from '@/components/icons/Money.vue'
import ChatGroupIcon from '@/components/icons/ChatGroup.vue'

const benefits = [
	{
		title: 'Official partner listing',
		description:
			'Get your own dedicated listing on our website unlocking client opportunities and visibility.',
		icon: Points1Icon,
	},
	{
		title: 'Lead sharing',
		description: 'Get access to qualified leads and interested clients.',
		icon: People1Icon,
	},
	{
		title: 'Partner discounts',
		description:
			'Get discounts on Frappe Cloud payments as a Gold, Silver & Bronze tier partner.',
		icon: MoneyIcon,
	},
	{
		title: 'Enterprise deal assistance',
		description:
			'Get a perfect closure to your deals with Frappe-backed advantages.',
		icon: ChatGroupIcon,
	},
]
</script>

<template>
	<div>
		<p class="text-p-base text-ink-gray-6 mb-4">
			Some of the benefits of partnering with us are:
		</p>

		<ul
			class="list-none list-inside"
			v-for="benefit in benefits"
			:key="benefit.title"
		>
			<li class="flex items-start gap-3 self-stretch mb-4">
				<component :is="benefit.icon" class="w-5 h-5" />
				<div class="flex flex-col gap-1 items-start flex-1">
					<p class="text-p-base font-medium text-ink-gray-8">
						{{ benefit.title }}
					</p>
					<p class="text-p-base text-ink-gray-6">
						{{ benefit.description }}
					</p>
				</div>
			</li>
		</ul>
	</div>
</template>
