(function () {
  "use strict";

  var selector = "img[data-src]";

  function loadImage(img) {
    var src = img.getAttribute("data-src");
    if (!src) return;

    img.addEventListener("load", function () {
      img.classList.add("is-loaded");
      img.removeAttribute("data-src");
    }, { once: true });

    img.src = src;
  }

  function initLazyImages() {
    var images = Array.prototype.slice.call(document.querySelectorAll(selector));
    if (!images.length) return;

    if (!("IntersectionObserver" in window)) {
      images.forEach(loadImage);
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting && entry.intersectionRatio <= 0) return;
        observer.unobserve(entry.target);
        loadImage(entry.target);
      });
    }, {
      rootMargin: "360px 0px",
      threshold: 0.01
    });

    images.forEach(function (img) {
      observer.observe(img);
    });
  }

  if (document.readyState === "complete") {
    window.setTimeout(initLazyImages, 0);
  } else {
    window.addEventListener("load", function () {
      window.setTimeout(initLazyImages, 0);
    }, { once: true });
  }
}());
