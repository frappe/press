class ListComponent {
    constructor(parent, df) {
        this.parent = parent;
        this.df = df || {};

        this.make();
    }

    make() {
        this.wrapper = $(`<div class="list-component">`).appendTo(this.parent);

        let html = this.iterate_list(this.df.data, this.df.template);
        this.wrapper.append(`${html}`);
    }

    iterate_list(data, template) {
        var html = '';
    
        for(var i = 0; i < data.length; i++) {
            html += template(data[i]);
            if(i != data.length - 1 ) html += '<hr class="mt-1">';
        }
        return html;
    }
}