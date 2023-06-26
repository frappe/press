class DetailedListComponent {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="detailed-list-component d-flex flex-row">`).appendTo(this.parent);
        
        let brief_section = $(`<div class="brief-section d-flex flex-column w-25 mr-4">`).appendTo(this.wrapper);
        $(`<div style="border-left:0.1px solid #DFDAD9">`).appendTo(this.wrapper);
        let detailed_section = $(`<div class="detailed-section d-flex flex-column w-75 ml-4">`).appendTo(this.wrapper);

        new SectionHead(brief_section, this.df);
        new SectionHead(detailed_section, {
            description: 'Nothing selected'
        });
        new ListComponent(brief_section, {
            data: this.df.data,
            template: this.df.template,
            onclick: (index) => {
                clear_wrapper(detailed_section);
                this.df.onclick(index, detailed_section);
            }
        });
	}
}