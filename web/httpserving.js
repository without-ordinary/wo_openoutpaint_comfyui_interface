import { app } from "../../../scripts/app.js";
import { api } from "../../scripts/api.js";

function QueuePrompt_MessageHandler(event) {
    let nodes = app.graph._nodes_by_id;
    let node = nodes[event.detail.node_id];
    console.debug(node);
	if(node && node.type == event.detail.node_type) {
        const port_widget = node.widgets.find((w) => w.name === "port");
        const request_id_widget = node.widgets.find((w) => w.name === "request_id");
        if(request_id_widget && port_widget && port_widget.value == event.detail.port) {
            request_id_widget.value = event.detail.request_id;
            console.debug("wo_QueuePrompt app.queuePrompt");
            app.queuePrompt(0, 1);
            return;
        }
	}
}

app.registerExtension({
	name: "wo.OpenOutpainterServing",
	async setup() {
	    api.addEventListener("wo_QueuePrompt", QueuePrompt_MessageHandler);
	},
})

