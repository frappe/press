<template>
	<div>
		<PageHeader v-if="siteName">
			<template slot="title">
				<div class="flex items-center">
					<router-link to="/sites" class="flex items-center">
						<FeatherIcon name="arrow-left" class="w-4 h-4" />
						<span class="ml-2 text-base">Back</span>
					</router-link>
				</div>
			</template>
		</PageHeader>
		<div class="px-8" v-if="site">
			<div class="border-t"></div>
			<div class="py-8">
				<div class="flex items-center">
					<h1 class="font-medium text-2xl">{{ site.name }}</h1>
					<Badge class="ml-4" :status="site.status">{{ site.status }}</Badge>
				</div>
				<a
					:href="`https://${site.name}`"
					target="_blank"
					class="inline-flex items-baseline hover:underline text-blue-500 text-sm"
				>
					Visit Site
					<FeatherIcon name="external-link" class="ml-1 w-3 h-3" />
				</a>
			</div>
			<!-- <table class="w-1/4 border-collapse text-sm">
				<tbody>
					<tr v-for="d in siteDetails" :key="d.label">
						<td class="border py-2 px-4">
							{{ d.label }}
						</td>
						<td class="border py-2 px-4">
							{{ d.value }}
						</td>
					</tr>
				</tbody>
			</table> -->
			<div class="mt-6" v-if="siteInstalling">
				<h2>{{ progress.runningStep }}</h2>
				<div class="rounded-md overflow-auto h-4 bg-blue-100">
					<div
						class="bg-blue-500 h-full"
						:style="`width: ${(progress.current + 1 / progress.total) * 100}%;`"
					></div>
				</div>
			</div>
		</div>
		<div class="px-8 mt-4">
			<div class="flex items-start">
				<ul class="w-56 border rounded overflow-hidden text-sm mr-6">
					<router-link
						v-for="tab in tabs"
						:key="tab.label"
						:to="tab.route"
						v-slot="{ href, route, navigate, isActive, isExactActive }"
					>
						<li class="-mt-px border-t">
							<a
								class="px-4 py-3 leading-none block focus:outline-none focus:bg-gray-100 focus:text-gray-900"
								:class="[
									isExactActive
										? 'font-bold border-brand border-l-2'
										: 'text-gray-800 hover:text-gray-900 hover:bg-gray-100'
								]"
								:href="href"
								@click="navigate"
							>
								{{ tab.label }}
							</a>
						</li>
					</router-link>
				</ul>
				<div class="w-full" v-if="site">
					<router-view v-bind="{ site }"></router-view>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import io from 'socket.io-client';

let steps = [
	'New Site',
	'Install Apps',
	'Site Update Configuration',
	'Bench Setup NGINX',
	'Reload NGINX'
];
export default {
	name: 'Site',
	props: ['siteName'],
	data: () => ({
		site: null,
		newSiteJob: null,
		siteInstalling: false,
		newSiteJobSteps: [],
		progress: {
			current: 0,
			total: 5,
			runningStep: null
		},
		socket: null,
		tabs: [
			{ label: 'General', route: 'general' },
			{ label: 'Analytics', route: 'analytics' },
			{ label: 'Backups', route: 'backups' },
			{ label: 'Site Config', route: 'site-config' },
			{ label: 'Console', route: 'console' },
			{ label: 'Drop Site', route: 'drop-site' },
			{ label: 'Settings', route: 'settings' }
		]
	}),
	async mounted() {
		await this.fetchSite();
		// if (this.site.status !== 'Active') {
		// 	this.updateStatus();
		// }
		this.socket = io('http://frappe-cloud:9000');
		this.socket.on('connect', () => {
			console.log('connected');
		});
		this.socket.on('disconnect', () => {
			console.log('disconnected');
		});

		this.socket.on('agent_job_update', data => {
			if (data.site === this.siteName) {
				this.siteInstalling = data.status === 'Running';
				this.progress.current = data.current.index;
				this.progress.runningStep = data.current.name;
				this.progress.total = data.current.total;
				if (data.current.index > data.current.total) {
					this.fetchSite();
				}
			}
			console.log(data);
		});
		if (this.$route.matched.length === 1) {
			let path = this.$route.fullPath;
			this.$router.replace(`${path}/general`);
		}
	},
	destroyed() {
		this.socket.disconnect();
	},
	methods: {
		async updateStatus() {
			if (!this.newSiteJob) {
				let res = await this.$call('frappe.client.get_value', {
					doctype: 'Agent Job',
					filters: {
						job_type: 'New Site',
						site: this.siteName
					},
					fieldname: 'name'
				});
				this.newSiteJob = res.name;
			}
			await this.fetchSite();
			await this.fetchJobSteps();

			if (this.site.status !== 'Active') {
				setTimeout(() => {
					this.updateStatus();
				}, 1000);
			}
		},
		async fetchSite() {
			this.site = await this.$call('frappe.client.get', {
				doctype: 'Site',
				name: this.siteName
			});
		},
		async fetchJobSteps() {
			this.newSiteJobSteps = await this.$call('frappe.client.get_list', {
				doctype: 'Agent Job Step',
				filters: {
					agent_job: this.newSiteJob
				},
				fields: ['step_name, status']
			});
			let jobsInOrder = steps.map(name =>
				this.newSiteJobSteps.find(d => d.step_name === name)
			);
			jobsInOrder.forEach((job, i) => {
				if (job.status === 'Running') {
					this.progress.runningStep = job.step_name;
				}
				if (job.status === 'Success') {
					this.progress.current = i + 1;
				}
			});
		}
	},
	computed: {
		siteDetails() {
			return [
				{
					label: 'Server',
					value: this.site.server
				},
				{
					label: 'Bench',
					value: this.site.bench
				}
				// {
				// 	label: 'Apps',
				// 	value: this.site.apps.map(a => a.app).join(', ')
				// }
			];
		}
	}
};
</script>
