class SectionHead {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="d-flex flex-column">`).appendTo(this.parent);
		let header_section = $(
			`<div class="d-flex flex-row justify-between mb-${
				this.df.button ? '2' : '3'
			}">`
		).appendTo(this.wrapper);
		if (this.df.title) {
			header_section.append(`
                <div class="head-title">
                    ${this.df.title || ''}
                </div>
            `);
		}
		if (this.df.button) {
			let action_button = $(`<div class="action-button d-flex align-items-center">`).appendTo(header_section);
			action_button.append(`
                <button class="btn btn-${this.df.button.tag || 'light'}">
                    <span>${this.df.button.title || ''}</span>
                </button
            `);
			
			if (this.df.button.onclick) {
				$(action_button).on('click', () => {
					this.df.button.onclick();
				});
			}
		}
		if (this.df.description) {
			this.wrapper.append(`
                <div class="d-flex flex-row mb-4">
                    <p>${this.df.description || ''}</p>
                </div>
            `);
		}
	}
}
