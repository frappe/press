<script setup>
import { computed, ref } from 'vue';
import useResource from '@/composables/resource';
import call from '../../controllers/call';

const props = defineProps({ app: Object, appName: String });

const benches = useResource({
	method: 'press.api.saas.get_benches',
	params: {
		name: props.appName
	},
	auto: true
});

const benchData = computed(() => {
	return benches.data;
});
</script>

<template>
	<div v-if="props.appName">
		<div class="pb-4">
			<div class="flex items-center justify-between">
				<div></div>
				<router-link
					type="primary"
					iconLeft="plus"
					:to="`/benches/new/${app.name}`"
				>
					<Button type="primary" icon-left="plus"> New Bench </Button>
				</router-link>
			</div>
		</div>
	</div>
	<div class="grid grid-cols-3 gap-4" v-if="benchData">
		<router-link
			v-for="group in benchData.groups"
			:to="`/benches/${group.name}/overview`"
		>
			<Card :title="group.title">
				<template #actions>
					<Badge :status="group.status" />
				</template>
				<hr class="mb-2" />
				<div class="flex items-center justify-between py-2">
					<p class="w-fit">Active Sites</p>
					<Badge class="w-fit" status="Updating"
						>• {{ group.active_sites }}</Badge
					>
				</div>
				<div class="flex items-center justify-between py-2">
					<p class="w-fit">Broken Sites</p>
					<Badge class="w-fit" status="Broken"
						>• {{ group.broken_sites }}</Badge
					>
				</div>
				<div class="flex items-center justify-between py-2">
					<p class="w-fit">Suspended Sites</p>
					<Badge class="w-fit" status="Pending"
						>• {{ group.suspended_sites }}</Badge
					>
				</div>
				<hr class="my-2" />
				Use for new signups
			</Card>
		</router-link>
	</div>
</template>
