/* Small progressive-enhancement script. The site works fine without it. */
(function () {
  "use strict";

  /* ---- Theme toggle -------------------------------------------------- */
  var root = document.documentElement;

  function currentTheme() {
    var stored = null;
    try { stored = localStorage.getItem("theme"); } catch (e) { /* private mode */ }
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  var toggle = document.querySelector(".theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
      toggle.setAttribute("aria-label", next === "dark" ? "Switch to light theme" : "Switch to dark theme");
    });
  }

  /* ---- Mobile navigation --------------------------------------------- */
  var navToggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".nav");
  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        nav.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- Header border once the page scrolls --------------------------- */
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-stuck", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---- Route carousels -------------------------------------------------- */
  /* Slide one is the route map. The arrows step on through that walk's
     photographs and wrap round back to the map. */
  function wireCarousel(carousel) {
    var slides = carousel.querySelectorAll(".carousel-slide");
    var nav = carousel.querySelector(".stack-nav");
    if (slides.length < 2 || !nav) return;

    var buttons = nav.querySelectorAll("button");
    var readout = nav.querySelector(".stack-count");
    var at = 0;


    function show(i) {
      at = (i + slides.length) % slides.length;
      Array.prototype.forEach.call(slides, function (slide, n) {
        var on = n === at;
        slide.classList.toggle("is-active", on);
        var link = slide.querySelector("a");
        if (link) {
          if (on) link.removeAttribute("tabindex");
          else link.setAttribute("tabindex", "-1");
        }
      });
      // the map is slide zero, so the photographs count from one
      readout.textContent = at === 0 ? "Map" : at + " / " + (slides.length - 1);

      // hidden slides never load, so warm the next one to avoid a blank beat
      var next = slides[(at + 1) % slides.length].querySelector("img");
      if (next) next.loading = "eager";
    }

    buttons[0].addEventListener("click", function () { show(at - 1); });
    buttons[1].addEventListener("click", function () { show(at + 1); });
    show(0);
  }
  Array.prototype.forEach.call(document.querySelectorAll(".route-carousel"), wireCarousel);

  /* ---- Lightbox -------------------------------------------------------- */
  /* Every photograph on the page lives in a walk's carousel, and clicking one
     opens it here at full size. */
  var SET = ".route-carousel";
  var strips = document.querySelectorAll(SET);
  if (strips.length) {
    var box = document.querySelector(".lightbox");
    var stage = box && box.querySelector(".lightbox-stage img");
    var counter = box && box.querySelector(".lightbox-count");
    var label = box && box.querySelector(".lightbox-label");
    var prevBtn = box && box.querySelector(".lb-prev");
    var nextBtn = box && box.querySelector(".lb-next");
    var closeBtn = box && box.querySelector(".lb-close");

    if (box && stage) {
      var group = [];
      var index = 0;
      var opener = null;

      function show(i) {
        index = (i + group.length) % group.length;
        var link = group[index];
        stage.src = link.getAttribute("href");
        stage.alt = link.querySelector("img").alt;
        counter.textContent = index + 1 + " of " + group.length;
        label.textContent = link.getAttribute("data-group") || "";
        prevBtn.disabled = nextBtn.disabled = group.length < 2;
      }

      function open(link) {
        group = Array.prototype.slice.call(link.closest(SET).querySelectorAll("a"));
        opener = link;
        show(group.indexOf(link));
        box.classList.add("is-open");
        box.removeAttribute("aria-hidden");
        document.body.style.overflow = "hidden";
        closeBtn.focus();
      }

      function close() {
        box.classList.remove("is-open");
        box.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
        stage.removeAttribute("src");
        if (opener) opener.focus();
      }

      Array.prototype.forEach.call(strips, function (strip) {
        strip.addEventListener("click", function (e) {
          var link = e.target.closest("a");
          if (!link || !strip.contains(link)) return;
          e.preventDefault();
          open(link);
        });
      });

      prevBtn.addEventListener("click", function () { show(index - 1); });
      nextBtn.addEventListener("click", function () { show(index + 1); });
      closeBtn.addEventListener("click", close);
      box.addEventListener("click", function (e) {
        if (e.target === box || e.target.classList.contains("lightbox-stage")) close();
      });
      document.addEventListener("keydown", function (e) {
        if (!box.classList.contains("is-open")) return;
        if (e.key === "Escape") close();
        else if (e.key === "ArrowLeft") show(index - 1);
        else if (e.key === "ArrowRight") show(index + 1);
      });
    }
  }

  /* ---- Reveal sections on scroll ------------------------------------- */
  var revealables = document.querySelectorAll(".reveal");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!revealables.length) return;

  if (reduce || !("IntersectionObserver" in window)) {
    revealables.forEach(function (el) { el.classList.add("is-visible"); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  revealables.forEach(function (el) { observer.observe(el); });
})();
