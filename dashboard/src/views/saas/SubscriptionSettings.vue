<script setup>
import { computed, ref } from 'vue';

let showDropAppDialog = ref(false);

let deactivate = () => {};

let drop = () => {};

let settings = computed(() => {
	return [
		{
			title: 'Deactivate App',
			desc: "The app won't be publicly accessible"
		},
		{
			title: 'Drop App',
			desc: 'Once you drop your app, there is no going back',
			text_color: 'red'
		}
	];
});
</script>

<template>
	<div class="sm:grid sm:grid-cols-2">
		<Card title="Settings">
			<ListItem
				title="Drop App"
				description="Once you drop your app, there is no going back"
			>
				<template #actions>
					<Button @click="() => (showDropAppDialog = true)">
						<span class="text-red-600">Drop App</span>
					</Button>
				</template>
			</ListItem>
		</Card>

		<Dialog title="Drop App" v-model="showDropAppDialog"> </Dialog>
	</div>
</template>
