(function () {
  document.documentElement.classList.add("js");

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function reveal() {
    var elements = Array.prototype.slice.call(document.querySelectorAll(".fade-up, [data-reveal]"));
    if (!elements.length) return;

    if (reduceMotion || !("IntersectionObserver" in window)) {
      elements.forEach(function (element) {
        element.classList.add("visible");
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      });
    }, {
      threshold: 0.14,
      rootMargin: "0px 0px -48px 0px"
    });

    elements.forEach(function (element, index) {
      if (!element.style.getPropertyValue("--reveal-index")) {
        element.style.setProperty("--reveal-index", String(index % 8));
      }
      observer.observe(element);
    });
  }

  function logoDepth() {
    if (reduceMotion || !window.matchMedia("(pointer: fine)").matches) return;

    var stage = document.querySelector(".hero-logo-stage");
    if (!stage) return;

    stage.addEventListener("pointermove", function (event) {
      var rect = stage.getBoundingClientRect();
      var x = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
      var y = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
      stage.style.setProperty("--pointer-x", x.toFixed(3));
      stage.style.setProperty("--pointer-y", y.toFixed(3));
    });

    stage.addEventListener("pointerleave", function () {
      stage.style.setProperty("--pointer-x", "0");
      stage.style.setProperty("--pointer-y", "0");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      reveal();
      logoDepth();
    });
  } else {
    reveal();
    logoDepth();
  }
})();
