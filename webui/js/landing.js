// Navbar — add border + shadow after scrolling past 40px
const navbar = document.getElementById('navbar');
window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
}, { passive: true });

// Scroll-reveal — add .is-visible when elements enter the viewport
const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);
document.querySelectorAll('.animate').forEach(el => revealObserver.observe(el));

// Waitlist form — swap form for thank-you message on submit
function handleWaitlist(e) {
  e.preventDefault();
  document.getElementById('waitlist-form').style.display = 'none';
  document.getElementById('waitlist-thankyou').style.display = 'flex';
}
