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

function format_date(data) {
    let value = data.map(d => {
        return d.date
    });
    return value; 
}