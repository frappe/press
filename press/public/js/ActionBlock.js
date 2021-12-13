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
        `);

        let action_button = $(`<div class="action-button d-flex align-items-center">`).appendTo(this.wrapper);
        action_button.append(`
            <button class="btn btn-${this.df.button.tag || "light"}">
                    <span>${this.df.button.title || ""}</span>
            </button>
        `);

        if (this.df.button.onclick) {
            $(action_button).on('click', () => {
                this.df.button.onclick();
            });
        }

        //TODO: handle button onclick event
    }
}