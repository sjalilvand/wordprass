/* شخصی‌سازی و دسترس‌پذیری — theme, font size, contrast, motion (localStorage) */
(function () {
  var body = document.body;
  function apply(key, cls, on) {
    body.classList.toggle(cls, on);
    try { localStorage.setItem(key, on ? "1" : "0"); } catch (e) {}
  }
  window.toggleDark = function () {
    apply("site_dark", "dark", !body.classList.contains("dark"));
    var btn = document.getElementById("themeBtn");
    if (btn) btn.innerHTML = body.classList.contains("dark") ? "\u2600" : "\u263D";
  };
  window.a11yFont = function (level) {
    body.classList.remove("fs-large", "fs-xlarge");
    if (level === 1) body.classList.add("fs-large");
    if (level === 2) body.classList.add("fs-xlarge");
    try { localStorage.setItem("site_fs", String(level)); } catch (e) {}
  };
  window.a11yContrast = function () {
    apply("site_contrast", "contrast", !body.classList.contains("contrast"));
  };
  window.a11yMotion = function () {
    apply("site_nomotion", "no-motion", !body.classList.contains("no-motion"));
  };
  window.toggleA11y = function () {
    document.getElementById("a11yBar").classList.toggle("open");
  };
  /* restore preferences */
  try {
    if (localStorage.getItem("site_dark") === "1") body.classList.add("dark");
    var fs = localStorage.getItem("site_fs");
    if (fs === "1") body.classList.add("fs-large");
    if (fs === "2") body.classList.add("fs-xlarge");
    if (localStorage.getItem("site_contrast") === "1") body.classList.add("contrast");
    if (localStorage.getItem("site_nomotion") === "1") body.classList.add("no-motion");
  } catch (e) {}
})();
