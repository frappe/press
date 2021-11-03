function clear_block(frm, block) {
    clear_wrapper(frm.get_field(block).$wrapper);
}

function clear_wrapper(wrapper) {
    wrapper.html('');
}

function remap(data, data_template) {
    let new_data = [];
    for(let d of data) {
        new_data.push(data_template(d));
    }
    return new_data;
}

function format_chart_date(data) {
    return remap(data, (d) => {
        if(d.date) {
            return {
                date: format_date_time(d.date, 1),
                toString() {
                    return format_date_time(d.date, 1);
                }
            }
        } else {
            return {
                date: ''
            }
        }
    })
}

function format_date_time(date_time, show_date=false, show_time=false) {
    date_time = new Date(date_time);
    let year = date_time.getFullYear();
    let month = date_time.toLocaleString('default', { month: 'long' });
    let date = date_time.getDate();
    let hours = date_time.getHours();
    let minutes = date_time.getMinutes();

    let render_date = show_date ? `${date} ${month} ${year}` : ``
    render_date += show_time ? (show_date ? `, ` : ``) + `${hours}:${minutes} GMT+5:30`: ``

    return render_date;
}