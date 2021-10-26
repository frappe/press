class ListComponent {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="list-component">`).appendTo(this.parent);
		this.iterate_list(
			this.wrapper,
			this.df.data,
			this.df.template,
			this.df.onclick
		);
	}

	iterate_list(parent, data, template) {
		for (var i = 0; i < data.length; i++) {
			let cursor_style = this.df.onclick ? 'cursor: pointer;' : '';
			let list_row = $(
				`<div id="${i}" class="item-row hover-shadow" style="${cursor_style}">`
			).appendTo(parent);
			data[i].last = i == data.length - 1;
			list_row.append(template(data[i]));
			if (this.df.onclick) {
				$(list_row).on('click', () => {
					this.df.onclick(list_row[0].id); // TODO pass index
				});
			}
		}
	}
}
// list component templates

function title_with_message_and_tag_template(data) {
	let title = data.title || '';
	let message = data.message || '';
	let tag = data.tag || '';
	let tag_type = data.tag_type || '';

	return `
        <div class="d-flex flex-column">
            <div class="d-flex flex-column">
                <h5>${title || ''}</h5>
            </div>
            <div class="d-flex flex-row justify-between">
                <p>${message || ''}</p>
                <p class="${tag_type}">${tag || ''}</p>
            </div>
        </div>
		${data.last ? `` : `<hr>`}
    `;
}
let log_template = (data) => `
	<div>
		<strong>${data.step_title}</strong>
		<br>
		<div class="mt-3 p-2 card bg-light text-dark border-0 rounded-sm">
			<span style="white-space: pre-line">${data.step_detail}</span>
		</div>
	</div>	
	<br>
`;
