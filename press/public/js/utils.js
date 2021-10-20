function clear_block(wrapper) {
    wrapper.html('');
}

function remap(data, data_template) {
    let new_data = [];
    for(let d of data) {
        new_data.push(data_template(d));
    }
    return new_data;
}