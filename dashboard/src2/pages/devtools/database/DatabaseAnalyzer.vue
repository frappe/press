<template>
	<Header class="sticky top-0 z-10 bg-white">
		<div
			class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
		>
			<div class="flex flex-row items-center gap-2">
				<!-- Title -->
				<Breadcrumbs
					:items="[
						{ label: 'Dev Tools', route: '/database-analyzer' },
						{ label: 'Database Analyzer', route: '/database-analyzer' }
					]"
				/>
			</div>
			<div class="flex flex-row gap-2">
				<LinkControl
					class="cursor-pointer"
					:options="{ doctype: 'Site', filters: { status: 'Active' } }"
					placeholder="Select a site"
					v-model="site"
				/>
				<Button
					iconLeft="refresh-ccw"
					variant="subtle"
					:loading="site && !isSQLEditorReady"
					:disabled="!site"
					@click="
						() =>
							fetchTableSchemas({
								reload: true
							})
					"
				>
					<span class="md:hidden">Schema</span>
					<span class="hidden md:inline">Refresh Schema</span>
				</Button>
			</div>
		</div>
	</Header>
	<div class="m-5">
		<!-- body -->
		<div class="mt-2 flex flex-col" v-if="isSQLEditorReady">
			<div class="overflow-hidden rounded border">hekki</div>
		</div>
		<div
			v-else-if="!site"
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
		>
			Select a site to get started
		</div>
		<div
			class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
			v-else
		>
			<Spinner class="w-4" /> Loading Table Schemas
		</div>
	</div>
</template>
<style scoped>
.output-container {
	@apply rounded border p-4 text-base text-gray-700;
}
</style>
<script>
import Header from '../../../components/Header.vue';
import { Tabs, Breadcrumbs } from 'frappe-ui';
import LinkControl from '../../../components/LinkControl.vue';

export default {
	name: 'DatabaseAnalyzer',
	components: {
		Header,
		Breadcrumbs,
		FTabs: Tabs,
		LinkControl
	},
	data() {
		return {
			site: null,
			errorMessage: null
		};
	},
	mounted() {},
	watch: {
		query() {
			window.localStorage.setItem(
				`sql_playground_query_${this.site}`,
				this.query
			);
		},
		site(site_name) {
			// reset state
			this.data = null;
			this.errorMessage = null;
			this.fetchTableSchemas({
				site_name: site_name
			});
		}
	},
	resources: {
		tableSchemas() {
			return {
				url: 'press.api.client.run_doc_method',
				initialData: {},
				auto: false,
				onSuccess: data => {
					if (data?.message?.loading) {
						setTimeout(this.fetchTableSchemas, 5000);
					}
				}
			};
		}
	},
	computed: {
		isSQLEditorReady() {
			if (this.$resources.tableSchemas.loading) return false;
			if (this.$resources.tableSchemas?.data?.message?.loading) return false;
			if (!this.$resources.tableSchemas?.data?.message?.data) return false;
			if (this.$resources.tableSchemas?.data?.message?.data == {}) return false;
			return true;
		}
	},
	methods: {
		fetchTableSchemas({ site_name = null, reload = false } = {}) {
			if (!site_name) site_name = this.site;
			if (!site_name) return;
			this.$resources.tableSchemas.submit({
				dt: 'Site',
				dn: site_name,
				method: 'fetch_database_table_schema',
				args: {
					reload
				}
			});
		}
	}
};
</script>
