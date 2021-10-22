class ActionBlock {
    constructor(parent, df) {
        this.parent = parent;
        this.df = df || {};

        this.make();
    }

    make () {
        this.wrapper = $(`<div class="d-flex flex-row justify-between mb-3">`).appendTo(this.parent);
        this.wrapper.append(`
            <div>
                <div class="mb-2">
                    <h5 class="">${this.df.title || ""}</h5>
                </div>
                <p>${this.df.description || ""}</p>
            </div>
            <div class="d-flex align-items-center">
                <button class="btn btn-${this.df.button.tag || "light"}">
                    <span>${this.df.button.title || ""}</span>
                </button>
            </div>
        `);

        //TODO: handle button onclick event
    }
}