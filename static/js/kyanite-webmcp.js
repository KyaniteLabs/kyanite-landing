(function registerKyaniteWebMcp() {
  "use strict";

  if (!navigator.modelContext || typeof navigator.modelContext.registerTool !== "function") return;

  var controller = new AbortController();
  var options = { signal: controller.signal };
  function textResult(text) { return { content: [{ type: "text", text: text }] }; }

  navigator.modelContext.registerTool({
    name: "list_kyanite_public_resources",
    description: "List KyaniteLabs public projects, products, writing, and implementation paths.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    execute: async function () {
      var response = await fetch("/ai-sitemap.json", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error("KyaniteLabs public inventory is unavailable.");
      return textResult(JSON.stringify(await response.json()));
    }
  }, options);

  navigator.modelContext.registerTool({
    name: "find_kyanite_implementation_path",
    description: "Find the public KyaniteLabs implementation route for a stated need without submitting a form.",
    inputSchema: {
      type: "object",
      properties: { need: { type: "string", minLength: 1, maxLength: 500 } },
      required: ["need"],
      additionalProperties: false
    },
    execute: function (input) {
      return textResult(
        "Need: " + input.need + "\nReview https://kyanitelabs.tech/implementation for fit. " +
        "A human must approve any submission at https://kyanitelabs.tech/implementation/intake. No form was submitted."
      );
    }
  }, options);

  window.addEventListener("pagehide", function () { controller.abort(); }, { once: true });
}());
