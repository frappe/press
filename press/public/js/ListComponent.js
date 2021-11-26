class ListComponent {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="list-component">`).appendTo(this.parent);
		if (this.df.description) {
			this.wrapper.append(`
				<div class="d-flex flex-row mb-4">
					<p>${this.df.description || ''}</p>
				</div>
			`);
		}
		this.iterate_list(
			this.wrapper,
			this.df.data,
			this.df.template,
			this.df.onclick,
			this.df.selectable,
			this.df.multiselect,
			this.df.onupdate
		);
	}

	iterate_list(parent, data, template) {
		let selected_index = null;
		let selected_indices = [];
		let prev_selected_list_row = null;
		for (var i = 0; i < data.length; i++) {
			let cursor_style = (this.df.onclick || this.df.selectable || this.df.multiselect) ? 'cursor: pointer;' : '';
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
			if (this.df.selectable && !this.df.multiselect) {
				$(list_row).on('click', () => {
					if (selected_index) {
						if (selected_index == list_row[0].id){
							selected_index = null;
						}
						else {
							selected_index = list_row[0].id
						}
					} else {
						selected_index = list_row[0].id;
					}
					
					if (prev_selected_list_row) {
						prev_selected_list_row.empty();
						data[prev_selected_list_row[0].id].selected = (prev_selected_list_row[0].id == selected_index);
						prev_selected_list_row.append(template(data[prev_selected_list_row[0].id]));

						if (prev_selected_list_row[0].id != selected_index) {
							prev_selected_list_row = null;
						}
					}

					list_row.empty();
					data[list_row[0].id].selected = (list_row[0].id == selected_index);
					list_row.append(template(data[list_row[0].id]));

					if (list_row[0].id == selected_index) {
						prev_selected_list_row = list_row;
					}

					this.df.onupdate(selected_index);
				})

			}
			if(this.df.multiselect) {
				$(list_row).on('click', () => {
					list_row.empty();
					if(data[list_row[0].id].selected) {
						selected_indices.splice(selected_indices.indexOf(list_row[0].id), 1);
					} else {
						selected_indices.push(list_row[0].id);
					}
					data[list_row[0].id].selected = (selected_indices.includes(list_row[0].id));
					list_row.append(template(data[list_row[0].id]));

					this.df.onupdate(selected_indices);
				})

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

function title_with_sub_text_tag_and_button_template(data) {
	return `
		<div class="d-flex flex-row justify-between">
			<p class="list-row-col ellipsis list-subject level">${data.title || ""}
			<p class="list-row-col ellipsis hidden-xs">${data.sub_text || ""}</p>
			<div class="list-row-col ellipsis hidden-xs">
				<p class="${data.tag_type}" ellipsis">${data.tag}</p>
			</div>
			<button class="btn btn-outline-primary ellipsis">
				${data.button.title}
			</button>
		</div>
		${data.last ? `` : `<hr>`}
	`;
}

function title_with_text_area_template(data) {
	return `
		<div class="mb-4">
			<h5>${data.title || ''}</h5>
			<div class="mt-3 p-2 card bg-light text-dark border-0 rounded-sm">
				<span style="white-space: pre-line">${data.message || ''}</span>
			</div>
		</div>	
	`;
}

function title_with_sub_text_and_check_checkbox(data) {
	return `
		<div class="d-flex flex-row justify-between">
			<p class="list-row-col ellipsis list-subject level">${data.title || ""}</p>
			<p class="list-row-col ellipsis hidden-xs">${data.sub_text || ""}</p>
			<input type="checkbox" ${data.selected ? 'checked': ''}>
		</div>
		${data.last ? `` : `<hr>`}
	`;
}

