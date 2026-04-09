/* ═══════════════════════════════════════
   Dr. Vijay Vasudevan — Shared JS
   ═══════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Scroll-triggered fade-ins ── */
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) e.target.classList.add('visible');
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

  /* ── Nav auto-hide on scroll ── */
  const nav = document.querySelector('.site-nav');
  let lastY = 0;

  window.addEventListener('scroll', () => {
    const y = window.pageYOffset;
    if (y > lastY && y > 140) {
      nav.classList.add('nav-hidden');
    } else {
      nav.classList.remove('nav-hidden');
    }
    lastY = y;
  }, { passive: true });

  /* ── Mobile menu toggle ── */
  const toggle = document.querySelector('.nav-toggle');
  const menu   = document.querySelector('.nav-menu');

  if (toggle && menu) {
    // Open / close on hamburger tap
    toggle.addEventListener('click', () => {
      const isOpen = menu.classList.toggle('open');
      toggle.classList.toggle('open', isOpen);
      toggle.setAttribute('aria-expanded', isOpen);
    });

    // Close when any nav link is tapped
    menu.querySelectorAll('a').forEach(a =>
      a.addEventListener('click', () => {
        menu.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      })
    );

    // Close when tapping anywhere outside the nav
    document.addEventListener('click', e => {
      if (!toggle.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove('open');
        toggle.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── Mark active nav link ── */
  const path = window.location.pathname.replace(/\/$/, '');
  document.querySelectorAll('.nav-menu a:not(.nav-cta-link)').forEach(a => {
    const href = a.getAttribute('href').replace(/\/$/, '');
    if (
      (path === '' && (href === '/' || href === '/index.html' || href === 'index.html')) ||
      (path && href && path.endsWith(href.replace('.html', '')))
    ) {
      a.classList.add('active');
    }
  });

});
