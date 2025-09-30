<template>
	<div class="flex flex-col">
		<Header class="bg-white">
			<div
				class="flex w-full flex-col gap-2 md:flex-row md:items-center md:justify-between"
			>
				<div class="flex flex-row items-center gap-2">
					<!-- Title -->
					<Breadcrumbs
						:items="[
							{ label: 'Dev Tools', route: { name: 'Log Browser' } }, // Dev tools has no seperate page as its own, so it doesn't need a different route
							{ label: 'Log Browser', route: { name: 'Log Browser' } },
						]"
					/>
				</div>
				<div class="flex flex-row gap-2">
					<FormControl
						class="w-20"
						type="select"
						:options="[
							{
								label: 'Select Mode',
								disabled: true,
							},
							{
								label: 'Bench',
								value: 'bench',
							},
							{
								label: 'Site',
								value: 'site',
							},
						]"
						:modelValue="mode"
						@update:modelValue="
							(e) => $router.push({ name: 'Log Browser', params: { mode: e } })
						"
					/>
					<LinkControl
						v-show="mode === 'site'"
						:options="{
							doctype: 'Site',
							filters: { status: 'Active' },
							initialData: [{ label: site, value: site }],
						}"
						placeholder="Select a site"
						:modelValue="site"
						@update:modelValue="
							(site) => {
								this.site = site;
								$router.push({
									name: 'Log Browser',
									params: { mode: 'site', docName: site },
								});
							}
						"
					/>
					<LinkControl
						class="w-52"
						v-show="mode === 'bench'"
						:options="{
							doctype: 'Bench',
							filters: { status: 'Active' },
							initialData: [
								{
									label: bench,
									value: bench,
								},
							],
						}"
						placeholder="Select a bench"
						:modelValue="bench"
						@update:modelValue="
							(bench) => {
								this.bench = bench;
								$router.push({
									name: 'Log Browser',
									params: { mode: 'bench', docName: bench },
								});
							}
						"
					/>
					<Tooltip text="This is an experimental feature">
						<div class="rounded-md bg-purple-100 p-1.5">
							<lucide-flask-conical class="h-4 w-4 text-purple-500" />
						</div>
					</Tooltip>
					<Button
						link="https://docs.frappe.io/cloud/devtools/log-browser"
						target="_blank"
					>
						<lucide-help-circle class="h-4 w-4" />
					</Button>
				</div>
			</div>
		</Header>
		<div class="flex">
			<div
				v-if="(mode === 'bench' && !bench) || (mode === 'site' && !site)"
				class="w-full"
			>
				<p
					class="flex h-full min-h-[80vh] w-full items-center justify-center gap-2 text-gray-700"
				>
					Select a {{ mode }} to view logs
				</p>
			</div>
			<div v-else-if="mode" class="flex h-full w-full">
				<LogList :mode="mode" :docName="docName" />
				<div class="m-4 flex h-full w-3/4 flex-col">
					<div
						v-if="$resources.log.loading"
						class="flex h-full min-h-[90vh] w-full items-center justify-center gap-2 text-gray-700"
					>
						<Spinner class="h-4 w-4" />
						<span> Fetching the log... </span>
					</div>
					<ErrorMessage
						v-else-if="$resources.log.error"
						:message="$resources.log.error"
					/>
					<LogViewer v-else-if="logId" :log="log" />
					<div
						v-else
						class="flex h-full min-h-[90vh] w-full items-center justify-center gap-2 text-gray-700"
					>
						Select a log to view
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import Header from '../../../components/Header.vue';
import LinkControl from '../../../components/LinkControl.vue';
import LogList from './LogList.vue';
import LogViewer from './LogViewer.vue';
import { Breadcrumbs } from 'frappe-ui';

export default {
	components: {
		Header,
		LogList,
		LogViewer,
		LinkControl,
		Breadcrumbs,
	},
	props: {
		mode: String,
		logId: String,
		docName: String,
	},
	mounted() {
		if (!this.mode) {
			this.$router.push({ name: 'Log Browser', params: { mode: 'bench' } });
		}
	},
	updated() {
		if (!this.mode) {
			this.$router.push({ name: 'Log Browser', params: { mode: 'bench' } });
		}
	},
	data() {
		return {
			site: this.mode === 'site' ? this.docName : null || null,
			bench: this.mode === 'bench' ? this.docName : null || null,
			searchLogQuery: '',
		};
	},
	resources: {
		log() {
			return {
				url: 'press.api.log_browser.get_log',
				params: {
					log_type: this.mode,
					doc_name: this.docName,
					log_name: this.logId,
				},
				initialData: [],
				auto: this.logId,
			};
		},
	},
	computed: {
		log() {
			return this.$resources.log?.data;
		},
	},
};
</script>
