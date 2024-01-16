<template>
	<div>
		<GenericList :options="options" />

		<Dialog
			v-model="showAppVersionDialog"
			:options="{ title: 'Apps', size: '3xl' }"
		>
			<template #body-content>
				<div class="mb-4 text-base font-medium">
					{{ $releaseGroup.getAppVersions.params.args.bench }}
				</div>
				<GenericList :options="appVersionOptions" />
			</template>
		</Dialog>
	</div>
</template>
<script>
import { getCachedDocumentResource } from 'frappe-ui';
import GenericList from '../components/GenericList.vue';
import { icon } from '../utils/components';

export default {
	name: 'ReleaseGroupBenchSites',
	props: ['releaseGroup'],
	data() {
		return {
			showAppVersionDialog: false
		};
	},
	mounted() {
		this.$releaseGroup.deployedVersions.fetch();
	},
	computed: {
		options() {
			let data = [];
			for (let version of this.deployedVersions.data || []) {
				data.push({
					name: version.name,
					status: version.status,
					isBench: true
				});
				for (let site of version.sites) {
					data.push(site);
				}
				if (version.sites.length === 0) {
					data.push({
						name: 'No sites'
					});
				}
			}

			return {
				data,
				columns: [
					{
						label: 'Site',
						fieldname: 'name',
						width: 2,
						class({ row }) {
							return row.isBench
								? 'text-gray-900 font-medium'
								: row.name == 'No sites'
								? 'text-gray-600 pl-2'
								: 'text-gray-900 pl-2';
						}
					},
					{
						label: 'Status',
						fieldname: 'status',
						type: 'Badge'
					},
					{
						label: 'Region',
						fieldname: 'cluster'
					},
					{
						label: 'Plan',
						fieldname: 'plan',
						format: value => {
							if (!value) return '';
							if (value.price_usd > 0) {
								let india = this.$team.doc.country == 'India';
								let currencySymbol =
									this.$team.doc.currency == 'INR' ? '₹' : '$';
								return `${currencySymbol}${
									india ? value.price_inr : value.price_usd
								} /mo`;
							}
							return value.plan_title;
						}
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						Button: ({ row }) => {
							if (!row.isBench) return;
							return {
								label: 'Show apps',
								variant: 'ghost',
								loading:
									this.$releaseGroup.getAppVersions.loading &&
									this.$releaseGroup.getAppVersions.params.args.bench ==
										row.name,
								onClick: async () => {
									await this.$releaseGroup.getAppVersions.submit({
										bench: row.name
									});
									this.showAppVersionDialog = true;
								}
							};
						}
					},
					{
						label: '',
						type: 'Button',
						align: 'right',
						width: '44px',
						Button({ row }) {
							if (!row.isBench) return;
							return {
								label: 'Options',
								button: {
									label: 'Options',
									variant: 'ghost',
									slots: {
										default: icon('more-horizontal')
									}
								},
								options: [
									{
										label: 'Delete',
										variant: 'ghost',
										onClick: () => {
											console.log('delete');
										}
									}
								]
							};
						}
					}
				],
				route(row) {
					if (!row.isBench && row.name != 'No sites') {
						return { name: 'Site Detail', params: { name: row.name } };
					}
				}
			};
		},
		appVersionOptions() {
			return {
				columns: [
					{
						label: 'App',
						fieldname: 'app'
					},
					{
						label: 'Repo',
						fieldname: 'repository',
						format(value, row) {
							return `${row.repository_owner}/${row.repository}`;
						},
						link: (value, row) => {
							return row.repository_url;
						}
					},
					{
						label: 'Branch',
						fieldname: 'branch',
						type: 'Badge'
					},
					{
						label: 'Commit',
						fieldname: 'hash',
						type: 'Badge',
						format(value, row) {
							return value.slice(0, 7);
						}
					},
					{
						label: 'Tag',
						fieldname: 'tag',
						type: 'Badge'
					}
				],
				data: this.$releaseGroup.getAppVersions.data
			};
		},
		deployedVersions() {
			return this.$releaseGroup.deployedVersions;
		},
		$releaseGroup() {
			return getCachedDocumentResource('Release Group', this.releaseGroup);
		}
	},
	components: { GenericList }
};
</script>
