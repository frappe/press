<script setup lang="ts">
import { createResource, Dialog } from 'frappe-ui'
import { computed, ref } from 'vue'
import ObjectList from '../ObjectList.vue'

const props = defineProps<{ bench: string; releaseGroup: string }>()

const show = ref(true)
const appVersions = createResource({
	url: 'press.api.client.run_doc_method',
	params: {
		dt: 'Release Group',
		dn: props.releaseGroup,
		method: 'get_app_versions',
		args: { bench: props.bench },
	},
	auto: true,
})

const listOptions = computed(() => ({
	columns: [
		{ label: 'App', fieldname: 'app' },
		{
			label: 'Repo',
			fieldname: 'repository',
			format: (value: string, row: any) =>
				`${row.repository_owner}/${row.repository}`,
			link: (value: string, row: any) => row.repository_url,
		},
		{ label: 'Branch', fieldname: 'branch', type: 'Badge' },
		{
			label: 'Commit',
			fieldname: 'hash',
			type: 'Badge',
			format: (value: string) => value.slice(0, 7),
			link: (value: string, row: any) =>
				`https://github.com/${row.repository_owner}/${row.repository}/commit/${value}`,
		},
		{ label: 'Tag', fieldname: 'tag', type: 'Badge' },
	],
	data: () => appVersions.data,
}))
</script>

<template>
	<Dialog v-model="show" :options="{ title: `Apps in ${bench}`, size: '6xl' }">
		<template #body-content>
			<ObjectList :options="listOptions" />
		</template>
	</Dialog>
</template>
