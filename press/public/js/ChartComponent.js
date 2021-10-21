class ChartComponent {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="chart-component">`).appendTo(this.parent);
        
        this.df.description = !this.df.data ? 'No data' : '';        
        new SectionHead(this.wrapper, this.df);   
        
		let chart_section = $(`<div class="chart">`).appendTo(this.wrapper);
        if(this.df.data) {
            new frappe.Chart(chart_section.get(0), {
                data: this.df.data,
                type: this.df.type, // or 'bar', 'line', 'scatter', 'pie', 'percentage'
                height: 250,
                colors: this.df.colors,
            });
        }
	}
}
