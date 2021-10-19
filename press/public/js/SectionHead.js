class SectionHead {
    constructor(parent, df) {
        this.parent = parent;
        this.df = df || {};

        this.make();
    }

    make() {
        this.wrapper = $(`<div class="d-flex flex-row justify-between mb-${this.df.button ? '2': '3'}">`).appendTo(this.parent);
        if (this.df.title) {
            this.wrapper.append(`
                <div class="head-title">
                    ${this.df.title || ""}
                </div>
            `);
        }
        if (this.df.button) {
            this.wrapper.append(`
                <button class="btn btn-${this.df.button.tag || "light"}">
                    <span>${this.df.button.title || ""}</span>
                </button
            `)
        }
        // TODO: add button onclick trigger
    }
}