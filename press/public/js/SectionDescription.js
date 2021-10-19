class SectionDescription {
    constructor(parent, df) {
        this.parent = parent;
        this.df = df || {};

        this.make();
    }

    make() {
        this.wrapper = $(`<div class="section-description d-flex flex-column">`).appendTo(this.parent);
        this.wrapper.append(`
            <div class="d-flex flex-row mb-4">
                <p>${this.df.description || ""}</p>
            </div>
        `);
    }
}