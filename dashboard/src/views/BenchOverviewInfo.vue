<template>
	<Card title="Bench info" subtitle="General information about your bench">
		<div class="divide-y">
			<div class="flex items-center justify-between py-3">
				<div>
					<div class="text-base text-gray-600">Title</div>
					<div class="text-base font-medium text-gray-900">
						{{ bench.title }}
					</div>
				</div>
				<Button @click="showEditTitleDialog = true">Edit</Button>
			</div>
			<div class="py-3" v-for="item in items" :key="item.label">
				<div class="text-base text-gray-600">{{ item.label }}</div>
				<div class="text-base font-medium text-gray-900">
					{{ item.value }}
				</div>
			</div>
			<ListItem
				v-if="bench.status !== 'Awaiting Deploy'"
				title="Drop Bench"
				description="Permanently delete the bench and related data"
			>
				<template slot="actions">
					<BenchDrop :bench="bench" v-slot="{ showDialog }">
						<Button @click="showDialog">
							<span class="text-red-600">Drop Bench</span>
						</Button>
					</BenchDrop>
				</template>
			</ListItem>
		</div>
		<Dialog title="Edit Title" v-model="showEditTitleDialog">
			<Input label="Title" type="text" v-model="benchTitle" />
			<ErrorMessage class="mt-4" :error="$resources.editTitle.error" />

			<template #actions>
				<div class="space-x-2">
					<Button @click="showEditTitleDialog = false">Cancel</Button>
					<Button
						type="primary"
						:loading="$resources.editTitle.loading"
						loadingText="Saving..."
						@click="$resources.editTitle.submit()"
					>
						Update
					</Button>
				</div>
			</template>
		</Dialog>
	</Card>
</template>
<script>
import BenchDrop from './BenchDrop.vue';

export default {
	name: 'BenchOverviewInfo',
	components: {
		BenchDrop
	},
	props: ['bench'],
	data() {
		return {
			showEditTitleDialog: false,
			benchTitle: this.bench.title
		};
	},
	resources: {
		editTitle() {
			return {
				method: 'frappe.client.set_value',
				params: {
					doctype: 'Release Group',
					name: this.bench.name,
					fieldname: 'title',
					value: this.benchTitle
				},
				validate() {
					if (this.benchTitle === this.bench.title) {
						return 'No changes in bench title';
					}
				},
				onSuccess() {
					this.showEditTitleDialog = false;
				}
			};
		}
	},
	computed: {
		items() {
			return [
				{
					label: 'Version',
					value: this.bench.version
				},
				{
					label: 'Created On',
					value: this.formatDate(this.bench.creation, 'DATE_FULL')
				}
			];
		}
	}
};
</script>
