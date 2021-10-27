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
let title_with_text_area_template = (data) => `
	<div class="mb-4">
		<h5>${data.title || ''}</h5>
		<div class="mt-3 p-2 card bg-light text-dark border-0 rounded-sm">
			<span style="white-space: pre-line">${data.message || ''}</span>
		</div>
	</div>	
`;

// not used just kept for reference purpose
let version_template = (data) => {
	return `
		<div class="d-flex flex-row justify-between">
			<p>${data.name}</p> 
			<span class="indicator-pill green">${data.length} sites</span>
		</div>
	`;
};

let app_template = (data) => {
	return `
		<div class="d-flex flex-column justify-between">
			<h5>${data.data.name}</h5>
			<p>${data.data.repository_owner}/${data.data.repository}:${data.data.branch}</p>	
		</div>
	`;
};

let deploys_template = (data) => {
	let date = new Date(data.data.creation);

	let month = date.toLocaleString('default', { month: 'long' });

	return `
		<div class="d-flex flex-column justify-between">
			<p>
			Deployed on ${date.getDate()} ${month} ${date.getFullYear()}, ${date.getHours()}:${date.getMinutes()} GMT+5:30
			</p>
		</div>
	`;
};