class ChartComponent {
	constructor(parent, df) {
		this.parent = parent;
		this.df = df || {};

		this.make();
	}

	make() {
		this.wrapper = $(`<div class="chart-component">`).appendTo(this.parent);
        new SectionHead(this.wrapper, this.df);
        
		let chart_section = $(`<div class="chart">`).appendTo(this.wrapper);
        if(this.df.data) {
            if(this.df.type === 'mixed-bars') {
                let mixed_bar_section = $(`<div class="mixed-bars mt-4">`).appendTo(chart_section);
                for(let value of this.df.data.datasets[0].values) {
                    var bar;
                    if(value === undefined) {
                        bar = `<div class="bg-light m-1 float-left" style="height: 40px; width: 2px">`;
                    } else if (value === 1) {
                        bar = `<div class="bg-success m-1 float-left" style="height: 40px; width: 2px">`;
                    } else if (value === 0) {
                        bar = `<div class="bg-danger m-1 float-left" style="height: 40px; width: 2px">`;
                    } else {
                        bar = `<div class="bg-warning m-1 float-left" style="height: 40px; width: 2px">`;
                    }
                    mixed_bar_section.append($(bar));
                }
            } else {
                new frappe.Chart(chart_section.get(0), {
                    data: this.df.data,
                    type: this.df.type, // or 'bar', 'line', 'scatter', 'pie', 'percentage'
                    height: 250,
                    colors: this.df.colors,
                });
            }
        } else {
            chart_section.append(`
                <table style="height: 250px"> 
                    <tbody>
                        <tr>
                            <td/>
                            <td class="align-middle text-center w-100 pb-4">No data yet</td>
                            <td/>
                        </tr>
                    </tbody>
                </table>
            `);
        }
	}
}