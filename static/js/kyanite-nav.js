(function() {
  function setMenuState(button, menu, open) {
    button.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-hidden", String(!open));
    menu.classList.toggle("open", open);
  }

  function initGeneratedMenu() {
    var header = document.querySelector(".topbar");
    var nav = header && header.querySelector(".nav");
    var links = nav && nav.querySelector(".nav-links");

    if (!header || !nav || !links || nav.querySelector(".menu-button")) return;

    var menuId = "mobileMenu";
    var button = document.createElement("button");
    var menu = document.createElement("div");

    button.className = "menu-button";
    button.type = "button";
    button.setAttribute("aria-label", "Open menu");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-controls", menuId);
    button.innerHTML = "<span></span><span></span>";

    menu.className = "mobile-menu";
    menu.id = menuId;
    menu.setAttribute("aria-hidden", "true");

    Array.prototype.forEach.call(links.querySelectorAll("a"), function(link) {
      var clone = link.cloneNode(true);
      clone.addEventListener("click", function() {
        setMenuState(button, menu, false);
      });
      menu.appendChild(clone);
    });

    button.addEventListener("click", function() {
      setMenuState(button, menu, !menu.classList.contains("open"));
    });

    document.addEventListener("keydown", function(event) {
      if (event.key === "Escape") setMenuState(button, menu, false);
    });

    nav.appendChild(button);
    header.insertAdjacentElement("afterend", menu);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGeneratedMenu);
  } else {
    initGeneratedMenu();
  }
})();
