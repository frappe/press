<script setup>
import { computed, ref } from 'vue';
import SiteDrop from '../SiteDrop.vue';

const props = defineProps({ site: Object });
</script>

<template>
	<div class="sm:grid sm:grid-cols-2">
		<Card title="Settings">
			<ListItem
				v-if="props.site.status !== 'Pending'"
				title="Drop Site"
				description="Once you drop site your site, there is no going back"
			>
				<template v-slot:actions>
					<SiteDrop :site="props.site" v-slot="{ showDialog }">
						<Button @click="showDialog">
							<span class="text-red-600">Drop Site</span>
						</Button>
					</SiteDrop>
				</template>
			</ListItem>
		</Card>
	</div>
</template>
