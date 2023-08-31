<template>
	<Card title="Bench Info" subtitle="General information about your bench">
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
				<template v-slot:actions> </template>
			</ListItem>
		</div>
		<Dialog
			:options="{
				title: 'Edit Title',
				actions: [
					{
						label: 'Update',
						variant: 'solid',
						loading: $resources.editTitle.loading,
						onClick: () => $resources.editTitle.submit()
					}
				]
			}"
			v-model="showEditTitleDialog"
		>
			<template v-slot:body-content>
				<FormControl label="Title" v-model="benchTitle" />
				<ErrorMessage class="mt-4" :message="$resources.editTitle.error" />
			</template>
		</Dialog>
	</Card>
</template>
<script>
export default {
	name: 'BenchOverviewInfo',
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
				url: 'press.api.bench.rename',
				params: {
					name: this.bench?.name,
					title: this.benchTitle
				},
				validate() {
					if (this.benchTitle === this.bench?.title) {
						return 'No changes in bench title';
					}
				},
				onSuccess() {
					this.showEditTitleDialog = false;
					this.bench.title = this.benchTitle;
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
