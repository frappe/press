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

function format_date_time(date_time, show_date=false, show_time=false) {
    var formated_date_time = '';
    var [date, full_time] = date_time.split(' ');
    var time = full_time.split('.')[0];
    if(show_date) formated_date_time += date
    if(show_time) formated_date_time += (`, ${time}`);

    return formated_date_time;
}