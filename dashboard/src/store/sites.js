export default {
	data() {
		return {
			all: [],
			site: {},
			state: null,
			fetched: false
		};
	},
	methods: {
		setupSocketListener() {
			if (this._socketSetup) return;
			this._socketSetup = true;

			this.$store.socket.on('agent_job_update', data => {
				if (data.name === 'New Site') {
					let siteName = data.site;
					if (data.status === 'Success') {
						this.fetchSite(siteName);
						this.fetchAll();
						this.$notify({
							title: 'Site creation complete!',
							message: 'Login to your site and complete the setup wizard',
							icon: 'check',
							color: 'green'
						});
					}
				}
			});
		},
		async fetchAll() {
			this.state = 'Fetching';
			this.all = await this.$call('press.api.site.all');
			this.state = 'Fetched';
			this.fetched = true;
		},
		async fetchSite(siteName) {
			let site = await this.$call('press.api.site.get', {
				name: siteName
			});
			this.$set(this.site, siteName, site);
		},
		async loginAsAdministrator(siteName) {
			let sid = await this.$call('press.api.site.login', {
				name: siteName
			});
			if (sid) {
				window.open(`https://${siteName}/desk?sid=${sid}`, '_blank');
			}
		}
	}
};
