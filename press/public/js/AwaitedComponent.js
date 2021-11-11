class AwaitedComponent {
    constructor(parent, df) {
        this.parent = parent;
		this.df = df || {};

        this.make();
    }

    async make() {
		this.wrapper = $(`<div class="list-component">`).appendTo(this.parent);
        new SectionHead(this.wrapper, {
            description: this.df.loading_message || 'Loading...'
        });

        let data = await this.df.promise;
        clear_wrapper(this.wrapper);
        this.df.onload(data);
    }
}