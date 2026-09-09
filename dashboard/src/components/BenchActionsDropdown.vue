<script setup lang="ts">
import { createListResource } from 'frappe-ui'
import { computed } from 'vue'
import releaseGroup from '../objects/group'
import { type BenchRow, getBenchOptions } from '../utils/benchOptions'
import { getDocResource } from '../utils/resource'
import ActionButton from './ActionButton.vue'

const props = defineProps<{
	bench: string
	releaseGroup: string
	benchRow?: BenchRow
	actionsAccess?: Record<string, boolean>
}>()

const group = getDocResource({
	doctype: 'Release Group',
	name: props.releaseGroup,
	whitelistedMethods: releaseGroup.whitelistedMethods,
})
const fetchedBench = createListResource({
	doctype: 'Bench',
	filters: { name: props.bench },
	fields: ['name', 'status'],
	pageLength: 1,
	auto: !props.benchRow,
})

const options = computed(() =>
	getBenchOptions({
		row: props.benchRow ?? fetchedBench.data?.[0],
		releaseGroup: props.releaseGroup,
		version: group.doc?.version,
		actionsAccess: props.actionsAccess,
	}),
)
</script>

<template>
	<div>
		<ActionButton :options="options" :actionsAccess="actionsAccess" />
	</div>
</template>
