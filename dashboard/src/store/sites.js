export default {
	data() {
		return {
            all: [],
            state: null,
            fetched: false
		};
	},
	methods: {
        async fetch() {
            this.state = 'Fetching';
            this.all = await this.$call('press.api.site.all');
            this.state = 'Fetched';
            this.fetched = true;
        }
	}
};
