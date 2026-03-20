window.scrollToKeywordHit = function(containerId, hitId) {
    const container = document.getElementById(containerId);
    if (!container) return false;

    container.querySelectorAll(".kw-current").forEach(el => {
        el.classList.remove("kw-current");
    });

    const target = container.querySelector(`#${hitId}`);
    if (!target) return false;

    target.classList.add("kw-current");
    target.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });

    return true;
};