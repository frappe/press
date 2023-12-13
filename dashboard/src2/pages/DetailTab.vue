<template>
	<div class="p-5">
		<div v-if="tab.type === 'list'">
			<ObjectList :options="listOptions" />
		</div>
		<div v-else-if="tab.type == 'Component'">
			<component :is="tab.component" v-bind="getProps(tab)" />
		</div>
		<div v-else>
			{{ tab.label }}
		</div>
	</div>
</template>
<script>
import ObjectList from '../components/ObjectList.vue';
export default {
	name: 'DetailTab',
	props: ['document', 'tab'],
	components: {
		ObjectList
	},
	methods: {
		getFilters(tab) {
			return tab.list.filters ? tab.list.filters(this.document) : {};
		},
		getProps(tab) {
			return tab.props ? tab.props(this.document) : {};
		}
	},
	computed: {
		listOptions() {
			return {
				...this.tab.list,
				filters: this.getFilters(this.tab),
				context: {
					documentResource: this.document
				}
			};
		}
	}
};
</script>
