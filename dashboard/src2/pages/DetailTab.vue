<template>
	<div>
		<div v-if="tab.type === 'list'">
			<ObjectList :list="listProp" />
		</div>
		<div v-else class="p-5">
			{{ tab.label }}
		</div>
	</div>
</template>
<script>
export default {
	name: 'DetailTab',
	props: ['document', 'tab'],
	methods: {
		getFilters(tab) {
			return tab.list.filters ? tab.list.filters(this.document) : {};
		}
	},
	computed: {
		listProp() {
			return {
				...this.tab.list,
				filters: this.getFilters(this.tab)
			};
		}
	}
};
</script>
