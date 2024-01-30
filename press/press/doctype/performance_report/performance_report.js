// Copyright (c) 2024, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Performance Report", {
	refresh(frm) {
        // hide row index and check box
        var css = document.createElement("style");
        css.type = "text/css";     
        var styles = `
        .row-index {display:none;}
        .row-check {display:none;}`;
        if (css.styleSheet) css.styleSheet.cssText = styles;
        else css.appendChild(document.createTextNode(styles));
        document.getElementsByTagName("head")[0].appendChild(css);
	},
});
