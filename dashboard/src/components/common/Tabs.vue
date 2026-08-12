<script setup lang="ts">
import { TabsIndicator, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'

import { computed } from 'vue'

type Tab = {
	label: string
	value?: string
	icon?: string
	route?: string
}

export interface TabProps {
	tabs: Tab[]
	tablistClass?: string
	vertical?: boolean
	variant?: 'solid' | 'line' | 'ghost'
	dir?: 'rtl' | 'ltr'
	size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<TabProps>(), {
	variant: 'line',
	size: 'md',
})

const model = defineModel<string | number>({ default: 0 })

const dir = computed<'rtl' | 'ltr'>(
	() =>
		props.dir ??
		(typeof document !== 'undefined' && document.documentElement.dir === 'rtl'
			? 'rtl'
			: 'ltr'),
)

const indicatorXCss = `left-0 bottom-0 h-[1px] w-[--reka-tabs-indicator-size] transition-[width,transform]
                          translate-x-[--reka-tabs-indicator-position] translate-y-[1px]`

const indicatorYCss = `end-0 top-0 w-[1px] h-[--reka-tabs-indicator-size]
                       translate-y-[--reka-tabs-indicator-position] transition-[height,transform]`

const txtCss =
	'hover:text-ink-gray-9 data-[state=active]:text-ink-gray-9 text-ink-gray-5'

defineSlots<{
	default?: (props: { tab: Tab; selected: boolean }) => any
	suffix?: (props: { tab: Tab }) => any
}>()

const btnSizeCss = {
	xs: 'py-1.5 text-xs',
	sm: 'py-1.5 px-3 text-sm',
	md: 'py-2.5 text-base',
}

const btnCss = {
	line: '',
	solid:
		'hover:bg-surface-gray-2 data-[state=active]:shadow data-[state=active]:bg-surface-white data-[state=active]:dark:bg-surface-gray-3 rounded',
	ghost:
		'hover:bg-surface-gray-2 data-[state=active]:bg-surface-gray-2 rounded',
}

const tablistCss = {
	line: 'border-b gap-5 px-5',
	solid: 'bg-surface-gray-1 text-ink-gray-9 rounded border',
	ghost: 'text-ink-gray-9 gap-1',
}
</script>

<template>
	<TabsRoot
		:dir
		:orientation="vertical ? 'vertical' : 'horizontal'"
		:default-value="tabs[0].label"
		v-model="model"
	>
		<TabsList
			class="relative flex data-[orientation=vertical]:flex-col data-[orientation=vertical]:border-e"
			:class="[tablistCss[variant], tablistClass]"
		>
			<TabsIndicator
				v-if="variant == 'line'"
				class="absolute rounded-full"
				:class="props.vertical ? indicatorYCss : indicatorXCss"
			>
				<div class="h-full w-full bg-surface-gray-7" />
			</TabsIndicator>

			<TabsTrigger
				as="template"
				v-for="(tab) in props.tabs"
				:value="tab.value || tab.label"
				:key="tab.value || tab.label"
			>
				<component
					:is="tab.route ? 'router-link' : 'BUTTON'"
					:to="tab.route"
					class="inline-flex items-center gap-1.5 text-ink-gray-5 ransition-all duration-300"
					:class="[ txtCss, btnCss[variant], btnSizeCss[size] ]"
				>
					<component v-if="tab.icon" :is="tab.icon" class="size-4" />
					{{ tab.label }}
					<slot name="suffix" v-bind="{ tab }" />
				</component>
			</TabsTrigger>
		</TabsList>
	</TabsRoot>
</template>
