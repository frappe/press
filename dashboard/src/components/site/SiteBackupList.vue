<template>
	<ObjectList class="p-5" :options="options" />
</template>

<script>
import { backupRecordsOptions } from '../../objects/site/backups'
import { getDocResource } from '../../utils/resource'
import ObjectList from '../ObjectList.vue'

export default {
	name: 'SiteBackupList',
	props: ['name'],
	components: { ObjectList },
	computed: {
		site() {
			return getDocResource({ doctype: 'Site', name: this.name })
		},
		options() {
			const options = backupRecordsOptions()
			return {
				...options,
				context: { documentResource: this.site },
				filters: options.filters(this.site),
			}
		},
	},
}
</script>
