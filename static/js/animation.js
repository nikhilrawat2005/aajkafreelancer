// Smooth diagonal lines animation using requestAnimationFrame
(function() {
    const overlay = document.querySelector('.diagonal-lines');
    if (!overlay) return;

    let position = 0;
    const speed = 0.02; // pixels per frame – slow and smooth

    function animate() {
        position += speed;
        // Keep within pattern size (24px pattern)
        if (position >= 24) position = 0;
        overlay.style.backgroundPosition = `${position}px ${position}px`;
        requestAnimationFrame(animate);
    }

    animate();
})();

// Scroll-based reveal animation for polished UI transitions
(function () {
    const candidates = [
        '.notebook-card',
        '.feature-box',
        '.stat-box',
        '.notebook-alert',
        '.skill-card-wrapper',
    ];

    const elements = document.querySelectorAll(candidates.join(','));
    if (!elements.length) return;

    elements.forEach((el) => el.setAttribute('data-reveal', 'true'));

    if (!('IntersectionObserver' in window)) {
        elements.forEach((el) => el.classList.add('is-visible'));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.12, rootMargin: '0px 0px -20px 0px' }
    );

    elements.forEach((el) => observer.observe(el));
})();